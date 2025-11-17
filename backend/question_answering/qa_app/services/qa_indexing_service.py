"""
QA Indexing Service
Indexes QA knowledge base entries into the vector store (Pinecone) and updates metadata.
"""

import logging
from typing import Optional, Dict, Any

from django.db import transaction
from django.utils import timezone

from qa_app.models import QAKnowledgeBase
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


class QAIndexingService:
    """Service responsible for pushing QA knowledge base entries into the vector index."""

    def __init__(self):
        self.rag_service = RAGService()
        self.logger = logging.getLogger(__name__)

    def _normalize_metadata_value(self, value: Any):
        """Coerce metadata values into Pinecone-supported primitives."""
        if value is None:
            return None
        if isinstance(value, (str, bool)):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, list):
            normalized = []
            for item in value:
                coerced = self._normalize_metadata_value(item)
                if coerced is None:
                    continue
                if isinstance(coerced, list):
                    normalized.extend([str(val) for val in coerced])
                elif isinstance(coerced, (int, float, bool)):
                    normalized.append(str(coerced))
                else:
                    normalized.append(coerced)
            return normalized if normalized else None
        if isinstance(value, dict):
            parts = []
            for key, val in value.items():
                coerced = self._normalize_metadata_value(val)
                if coerced is None:
                    continue
                if isinstance(coerced, list):
                    parts.append(f"{key}: {', '.join(str(item) for item in coerced)}")
                else:
                    parts.append(f"{key}: {coerced}")
            return ", ".join(parts) if parts else None
        return str(value)

    def _build_metadata(self, entry: QAKnowledgeBase) -> Dict[str, Any]:
        """Create metadata dictionary for the vector store."""
        metadata = {
            'title': entry.title or '',
            'case_number': entry.case_number or '',
            'case_title': entry.case_title or '',
            'court': entry.court or '',
            'judge_name': entry.judge_name or '',
            'legal_domain': entry.legal_domain or '',
            'created_at': entry.created_at.isoformat(),
            'qa_relevance': float(entry.legal_relevance_score or 0.0),
            'qa_quality': float(entry.content_quality_score or 0.0),
        }

        # Add trimmed content snapshots so retrievers can access textual context directly
        content_text = entry.content_text or ''
        metadata['text'] = content_text[:1000]
        metadata['content'] = content_text[:2000]
        metadata['source_type'] = entry.source_type or ''

        if entry.source_case_id is not None:
            metadata['case_id'] = entry.source_case_id
        if entry.source_document_id is not None:
            metadata['document_id'] = str(entry.source_document_id)

        # Flatten structured entities (advocates, FIR data, orders, etc.) into metadata
        structured_entities = {}
        for entity in entry.legal_entities or []:
            entity_type = entity.get('type') if isinstance(entity, dict) else None
            entity_value = entity.get('value') if isinstance(entity, dict) else None
            if not entity_type or entity_value in (None, '', []):
                continue

            key = f"entity_{entity_type}"
            value = entity_value

            if key not in structured_entities:
                structured_entities[key] = value if isinstance(value, list) else [value]
            else:
                existing = structured_entities[key]
                if not isinstance(existing, list):
                    existing = [existing]
                if isinstance(value, list):
                    existing.extend(value)
                else:
                    existing.append(value)
                structured_entities[key] = existing

        for key, value in structured_entities.items():
            normalized = self._normalize_metadata_value(value)
            if normalized in (None, []):
                continue
            if isinstance(normalized, list):
                normalized = [val if isinstance(val, str) else str(val) for val in normalized]
            metadata[key] = normalized

        # Final cleanup: remove unsupported None values
        cleaned_metadata = {}
        for key, value in metadata.items():
            normalized = self._normalize_metadata_value(value)
            if normalized in (None, []):
                continue
            cleaned_metadata[key] = normalized

        return cleaned_metadata

    def index_entry(self, entry: QAKnowledgeBase, force: bool = False) -> bool:
        """Index a single QA knowledge base entry."""
        # Skip entries without usable content
        content = entry.content_text or entry.content_summary
        if not content or not content.strip():
            self.logger.debug("Skipping QA entry %s due to empty content", entry.id)
            return False

        # Prepare deterministic vector/document ID using content hash
        vector_id = f"qa_{entry.id}_{entry.content_hash[:16]}"

        success = self.rag_service.index_document(
            case_id=entry.source_case_id or 0,
            document_id=entry.source_document_id,
            content=content,
            content_type=entry.source_type or "qa_chunk",
            metadata=self._build_metadata(entry),
            doc_id=vector_id
        )

        with transaction.atomic():
            if success:
                entry.is_indexed = True
                entry.processing_error = ""
                entry.indexed_at = timezone.now()
                entry.save(update_fields=['is_indexed', 'processing_error', 'indexed_at'])
                return True

            # Mark failure but keep record for visibility
            entry.is_indexed = False
            entry.processing_error = "Vector indexing failed"
            entry.save(update_fields=['is_indexed', 'processing_error'])
            return False

    def index_queryset(self, queryset, force: bool = False, batch_size: int = 50) -> Dict[str, int]:
        """
        Index entries from the provided queryset.

        Args:
            queryset: Django queryset of QAKnowledgeBase entries.
            force: When True, process entries even if already indexed.
            batch_size: Chunk size for queryset iteration.
        """
        stats = {
            'total': 0,
            'indexed': 0,
            'failed': 0,
            'skipped': 0,
        }

        if not self.rag_service.pinecone_index:
            self.logger.warning("Pinecone index is not available; indexing cannot proceed.")
            return stats

        iterator = queryset.iterator(chunk_size=batch_size)
        for entry in iterator:
            stats['total'] += 1

            if entry.is_indexed and not force:
                stats['skipped'] += 1
                continue

            if self.index_entry(entry, force=force):
                stats['indexed'] += 1
            else:
                stats['failed'] += 1

        return stats

