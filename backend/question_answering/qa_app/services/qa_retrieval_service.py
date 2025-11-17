"""
QA Retrieval Service
Implements two-stage retrieval with cross-encoder reranking for Question-Answering
"""

import os
import re
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone import Pinecone
import hashlib
import pickle
import os
from django.conf import settings

logger = logging.getLogger(__name__)


class QARetrievalService:
    """
    Advanced QA Retrieval Service implementing two-stage retrieval:
    1. Initial broad semantic retrieval (top-30)
    2. Cross-encoder reranking for quality (top-8-12)
    """
    
    def __init__(self):
        """Initialize QA retrieval service with two-stage retrieval"""
        self.embedding_model = None
        self.cross_encoder = None
        self.pinecone_client = None
        self.pinecone_index = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2
        self.case_metadata_cache: Dict[int, Dict[str, Any]] = {}
        
        # QA-specific configuration
        self.config = {
            'initial_retrieval_k': 30,      # Stage 1: Broad retrieval
            'final_retrieval_k': 12,        # Stage 2: Quality reranking
            'min_rerank_k': 8,              # Minimum results after reranking
            'semantic_weight': 0.7,         # Weight for semantic similarity
            'qa_relevance_weight': 0.3,     # Weight for QA-specific relevance
            'diversity_threshold': 0.8,     # MMR diversity threshold
            'cross_encoder_model': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        }
        
        # Embedding cache for performance optimization
        self.embedding_cache = {}
        self.cache_dir = getattr(settings, 'EMBEDDING_CACHE_DIR', '/tmp/qa_embeddings_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize components
        self._initialize_embedding_model()
        self._initialize_cross_encoder()
        self._initialize_pinecone()
    
    # -----------------------------
    # Unified view helpers
    # -----------------------------
    def _flatten_meta(self, data: Any, prefix: str = "", out: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Flatten nested dict/list metadata to make robust key lookups."""
        if out is None:
            out = {}
        try:
            if isinstance(data, dict):
                for k, v in data.items():
                    key = f"{prefix}.{k}".strip(".").lower()
                    self._flatten_meta(v, key, out)
            elif isinstance(data, list):
                for idx, v in enumerate(data):
                    key = f"{prefix}.{idx}".strip(".").lower()
                    self._flatten_meta(v, key, out)
            else:
                out[prefix.lower()] = data
        except Exception:
            pass
        return out
    
    def _get_meta_value(self, meta: Dict[str, Any], aliases: List[str]) -> Optional[str]:
        """Return first value that matches any alias across flattened keys."""
        if not meta:
            return None
        flat = self._flatten_meta(meta)
        for alias in aliases:
            alias_l = alias.lower()
            # direct key
            if alias_l in flat and flat[alias_l] not in (None, '', []):
                return str(flat[alias_l])
            # contains match
            for k, v in flat.items():
                if alias_l in k and v not in (None, '', []):
                    return str(v)
        return None
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer for semantic search"""
        try:
            model_name = "all-MiniLM-L6-v2"
            logger.info(f"Loading QA embedding model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"QA embedding model loaded. Dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to load QA embedding model: {str(e)}")
            self.embedding_model = None
    
    def _initialize_cross_encoder(self):
        """Initialize cross-encoder for quality reranking"""
        try:
            model_name = self.config['cross_encoder_model']
            logger.info(f"Loading QA cross-encoder: {model_name}")
            self.cross_encoder = CrossEncoder(model_name)
            logger.info("QA cross-encoder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load QA cross-encoder: {str(e)}")
            self.cross_encoder = None
    
    def _initialize_pinecone(self):
        """Initialize Pinecone for vector storage"""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            
            if not api_key:
                logger.warning("PINECONE_API_KEY not found. QA retrieval will use fallback methods.")
                return
            
            self.pinecone_client = Pinecone(api_key=api_key)
            
            # Use QA-specific index
            from core.settings import PINECONE_INDEX_NAME
            index_name = PINECONE_INDEX_NAME
            if index_name in self.pinecone_client.list_indexes().names():
                self.pinecone_index = self.pinecone_client.Index(index_name)
                logger.info(f"Connected to QA Pinecone index: {index_name}")
            else:
                logger.warning(f"QA Pinecone index '{index_name}' not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone for QA: {str(e)}")
            self.pinecone_client = None
            self.pinecone_index = None
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text to use as cache key"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cached_embeddings(self, texts: List[str]) -> Tuple[List[np.ndarray], List[str]]:
        """Get cached embeddings for texts, return (embeddings, uncached_texts)"""
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            text_hash = self._get_text_hash(text)
            cache_file = os.path.join(self.cache_dir, f"{text_hash}.pkl")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        embedding = pickle.load(f)
                    cached_embeddings.append((i, embedding))
                except Exception as e:
                    logger.warning(f"Failed to load cached embedding: {str(e)}")
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        return cached_embeddings, uncached_texts, uncached_indices
    
    def _cache_embeddings(self, texts: List[str], embeddings: np.ndarray) -> None:
        """Cache embeddings for texts"""
        for text, embedding in zip(texts, embeddings):
            text_hash = self._get_text_hash(text)
            cache_file = os.path.join(self.cache_dir, f"{text_hash}.pkl")
            
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(embedding, f)
            except Exception as e:
                logger.warning(f"Failed to cache embedding: {str(e)}")
    
    def _get_embeddings_with_cache(self, texts: List[str]) -> np.ndarray:
        """Get embeddings with caching support"""
        if not self.embedding_model:
            return np.array([])
        
        # Get cached embeddings
        cached_embeddings, uncached_texts, uncached_indices = self._get_cached_embeddings(texts)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            logger.info(f"Generating embeddings for {len(uncached_texts)} uncached texts")
            new_embeddings = self.embedding_model.encode(uncached_texts, batch_size=32, show_progress_bar=False)
            self._cache_embeddings(uncached_texts, new_embeddings)
        else:
            new_embeddings = np.array([])
        
        # Combine cached and new embeddings in correct order
        all_embeddings = np.zeros((len(texts), self.embedding_dimension))
        
        # Fill in cached embeddings
        for i, embedding in cached_embeddings:
            all_embeddings[i] = embedding
        
        # Fill in new embeddings
        for i, embedding in zip(uncached_indices, new_embeddings):
            all_embeddings[i] = embedding
        
        cache_hit_rate = len(cached_embeddings) / len(texts) * 100
        logger.info(f"Embedding cache hit rate: {cache_hit_rate:.1f}% ({len(cached_embeddings)}/{len(texts)})")
        
        return all_embeddings
    
    def _entities_to_structured(self, entities: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Convert legal_entities lists into a consolidated metadata dictionary."""
        structured: Dict[str, Any] = {}
        if not entities:
            return structured
        
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            entity_type = entity.get('type')
            value = entity.get('value')
            if not entity_type or value in (None, '', []):
                continue
            key = entity_type
            processed_value: Any = value
            if isinstance(processed_value, str):
                processed_value = processed_value.strip()
                if not processed_value:
                    continue
            
            if key not in structured:
                structured[key] = processed_value
            else:
                existing = structured[key]
                if not isinstance(existing, list):
                    existing = [existing]
                if isinstance(processed_value, list):
                    existing.extend(processed_value)
                else:
                    existing.append(processed_value)
                structured[key] = existing
        
        return structured
    
    def retrieve_for_qa(self, 
                       query: str, 
                       top_k: int = 10,
                       legal_domain: Optional[str] = None,
                       case_type: Optional[str] = None,
                       court_filter: Optional[str] = None,
                       year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Two-stage retrieval optimized for QA:
        1. Check for exact case number match first (priority)
        2. Initial broad semantic retrieval (top-30)
        3. Cross-encoder reranking for quality (top-8-12)
        
        Args:
            query: User's question
            top_k: Final number of results to return
            legal_domain: Filter by legal domain (criminal, civil, etc.)
            case_type: Filter by case type (judgment, order, decree)
            court_filter: Filter by court
            year_filter: Filter by year
            
        Returns:
            List of ranked results optimized for QA context
        """
        try:
            logger.info(f"Starting QA retrieval for query: '{query[:50]}...'")
            start_time = datetime.now()
            
            # Stage 0: Check for exact case number match FIRST (before semantic search)
            case_title_hint = self._extract_case_title_from_question(query)
            if case_title_hint:
                logger.info(f"Extracted case title hint: '{case_title_hint}' from query")
                exact_match_results = self._find_exact_case_match(case_title_hint)
                if exact_match_results:
                    logger.info(f"[SUCCESS] Found {len(exact_match_results)} exact case match(es) for: {case_title_hint}")
                    # If exact match found, use ONLY exact matches (don't mix with semantic search)
                    # This ensures we return the correct case, not similar ones
                    initial_results = exact_match_results
                    # Optionally add semantic search results for additional context, but keep exact matches first
                    # semantic_results = self._initial_semantic_retrieval(
                    #     query, self.config['initial_retrieval_k'],
                    #     legal_domain, case_type, court_filter, year_filter
                    # )
                    # # Prepend exact matches, remove duplicates
                    # seen_ids = {r.get('metadata', {}).get('case_id') or r.get('case_id') for r in exact_match_results}
                    # for result in semantic_results:
                    #     case_id = result.get('metadata', {}).get('case_id') or result.get('case_id')
                    #     if case_id not in seen_ids:
                    #         initial_results.append(result)
                    #         seen_ids.add(case_id)
                else:
                    logger.warning(f"❌ No exact case match found for: {case_title_hint}, falling back to semantic search")
                    # No exact match, proceed with normal semantic search
                    initial_results = self._initial_semantic_retrieval(
                        query, 
                        self.config['initial_retrieval_k'],
                        legal_domain, case_type, court_filter, year_filter
                    )
            else:
                logger.info("No case title detected in query, using semantic search only")
                # No case title detected, proceed with normal semantic search
                initial_results = self._initial_semantic_retrieval(
                    query, 
                    self.config['initial_retrieval_k'],
                    legal_domain, case_type, court_filter, year_filter
                )
            
            if not initial_results:
                logger.warning("No results from initial semantic retrieval")
                return []
            
            logger.info(f"Stage 1: Retrieved {len(initial_results)} initial results")
            
            # Stage 2: Cross-encoder reranking for quality
            if self.cross_encoder and len(initial_results) > 1:
                reranked_results = self._cross_encoder_reranking(
                    query, initial_results, min(top_k, self.config['final_retrieval_k'])
                )
                logger.info(f"Stage 2: Reranked to {len(reranked_results)} high-quality results")
            else:
                # Fallback: Use initial results with simple ranking
                reranked_results = initial_results[:top_k]
                logger.info("Using initial results (cross-encoder not available)")
            
            # Stage 3: Apply diversity control (MMR)
            final_results = self._apply_diversity_control(reranked_results, top_k)

            # Stage 4: Prioritize results that match detected case title
            case_title_hint = self._extract_case_title_from_question(query)
            if case_title_hint:
                final_results = self._filter_results_by_case_title(final_results, case_title_hint)

            # Add QA-specific metadata
            for i, result in enumerate(final_results):
                result['qa_rank'] = i + 1
                # Use combined_score if available (from cross-encoder), otherwise use original score
                # Ensure all scores are Python floats to avoid JSON serialization issues
                final_score = float(result.get('combined_score', result.get('score', 0.0)))
                result['qa_relevance_score'] = final_score
                result['score'] = final_score  # Update the main score field too
                result['retrieval_method'] = 'two_stage_qa'
                result['retrieval_time'] = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"QA retrieval completed: {len(final_results)} results in {result['retrieval_time']:.3f}s")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in QA retrieval: {str(e)}")
            return []
    
    def _initial_semantic_retrieval(self, 
                                  query: str, 
                                  top_k: int,
                                  legal_domain: Optional[str] = None,
                                  case_type: Optional[str] = None,
                                  court_filter: Optional[str] = None,
                                  year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Stage 1: Initial broad semantic retrieval"""
        try:
            if not self.pinecone_index or not self.embedding_model:
                logger.warning("Pinecone or embedding model not available, using fallback")
                return self._fallback_retrieval(query, top_k, legal_domain, case_type, court_filter, year_filter)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            
            # Prepare filters for Pinecone (using actual metadata fields)
            pinecone_filters = {}
            if legal_domain:
                # Skip legal_domain filtering as it's not in current metadata
                logger.warning(f"Legal domain filtering not available in current metadata: {legal_domain}")
                # Don't add to pinecone_filters to avoid filtering
            if case_type:
                # Map case_type to available fields - use status as proxy
                if case_type.lower() in ['pending', 'decided']:
                    pinecone_filters['status'] = case_type.title()
                else:
                    logger.warning(f"Case type filtering not available in current metadata: {case_type}")
            if court_filter:
                pinecone_filters['court'] = court_filter
            if year_filter:
                # Map year_filter to institution_date - Pinecone expects numeric values
                # For now, skip year filtering as it requires date parsing
                logger.warning(f"Year filtering not implemented for Pinecone: {year_filter}")
            
            # Search Pinecone
            search_params = {
                'vector': query_embedding.tolist(),
                'top_k': top_k,
                'include_metadata': True
            }
            
            if pinecone_filters:
                search_params['filter'] = pinecone_filters
            
            search_results = self.pinecone_index.query(**search_params)
            
            # Process results
            results = []
            for match in search_results.matches:
                metadata = match.metadata
                result_text = metadata.get('text') or metadata.get('content') or ''

                structured_data = {}
                for key, value in metadata.items():
                    if key.startswith('entity_') and value not in (None, '', []):
                        structured_data[key.replace('entity_', '')] = value
 
                case_id = metadata.get('case_id')
                if (not structured_data) and case_id is not None:
                    enriched = self._get_case_metadata_structured(case_id, query_embedding)
                    enriched_meta = enriched.get('metadata') if enriched else {}
                    enriched_structured = enriched.get('structured_data') if enriched else {}

                    if enriched_meta:
                        for meta_key, meta_value in enriched_meta.items():
                            if meta_key not in metadata and meta_value not in (None, '', []):
                                metadata[meta_key] = meta_value

                        if enriched_structured:
                            structured_data = enriched_structured or structured_data

                    if enriched_structured:
                        structured_summary = self._format_structured_snippet(enriched_structured)
                        if structured_summary:
                            metadata['structured_summary'] = structured_summary
                            if result_text:
                                result_text = f"{structured_summary}\n\n{result_text}"
                            else:
                                result_text = structured_summary

                result = {
                    'id': match.id,
                    'score': match.score,
                    'text': result_text,
                    'metadata': metadata,
                    'retrieval_stage': 'initial_semantic',
                    'source': 'Pinecone',
                    'file_name': metadata.get('file_name', 'Unknown'),
                    'case_title': metadata.get('case_title', 'Unknown'),
                    'case_number': metadata.get('case_number', 'Unknown'),
                    'structured_data': structured_data
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in initial semantic retrieval: {str(e)}")
            return self._fallback_retrieval(query, top_k)

    def _get_case_metadata_structured(self, case_id: Any, query_embedding: np.ndarray) -> Dict[str, Any]:
        """Fetch cached structured metadata for a case from Pinecone when missing."""
        try:
            if not self.pinecone_index or query_embedding.size == 0:
                return {}

            try:
                numeric_case_id = int(float(case_id))
            except (TypeError, ValueError):
                return {}

            if numeric_case_id in self.case_metadata_cache:
                return self.case_metadata_cache[numeric_case_id]

            filter_payload = {
                'case_id': {'$eq': numeric_case_id},
                'source_type': {'$eq': 'case_metadata'}
            }

            response = self.pinecone_index.query(
                vector=query_embedding.tolist(),
                top_k=1,
                include_metadata=True,
                filter=filter_payload
            )

            matches = getattr(response, 'matches', [])
            if not matches:
                self.case_metadata_cache[numeric_case_id] = {}
                return {}

            metadata = matches[0].metadata or {}
            structured_data = {
                key.replace('entity_', ''): value
                for key, value in metadata.items()
                if key.startswith('entity_') and value not in (None, '', [])
            }

            enriched = {
                'metadata': metadata,
                'structured_data': structured_data
            }
            self.case_metadata_cache[numeric_case_id] = enriched
            return enriched

        except Exception as ex:
            logger.warning(f"Failed to enrich case metadata for case {case_id}: {ex}")
            return {}

    def _cross_encoder_reranking(self, 
                               query: str, 
                               initial_results: List[Dict[str, Any]], 
                               top_k: int) -> List[Dict[str, Any]]:
        """Stage 2: Cross-encoder reranking for quality"""
        try:
            if not self.cross_encoder or len(initial_results) <= 1:
                return initial_results[:top_k]
            
            # Prepare query-document pairs
            pairs = []
            for result in initial_results:
                text = result.get('text', '')
                if text:
                    pairs.append((query, text))
                else:
                    pairs.append((query, ''))
            
            # Get cross-encoder scores
            rerank_scores = self.cross_encoder.predict(pairs)
            
            # Normalize cross-encoder scores to 0-1 range
            if len(rerank_scores) > 0:
                min_score = min(rerank_scores)
                max_score = max(rerank_scores)
                
                # Avoid division by zero
                if max_score == min_score:
                    normalized_scores = [0.5] * len(rerank_scores)
                else:
                    # Normalize to 0-1 range
                    normalized_scores = [(score - min_score) / (max_score - min_score) for score in rerank_scores]
            else:
                normalized_scores = []
            
            # Combine with initial scores
            for i, result in enumerate(initial_results):
                initial_score = float(result.get('score', 0.0))  # Ensure Python float
                raw_rerank_score = float(rerank_scores[i])  # Convert NumPy float32 to Python float
                normalized_rerank_score = float(normalized_scores[i]) if i < len(normalized_scores) else 0.0
                
                # Weighted combination: 70% cross-encoder + 30% initial
                combined_score = float(
                    self.config['semantic_weight'] * normalized_rerank_score +
                    (1 - self.config['semantic_weight']) * initial_score
                )
                
                result['rerank_score'] = raw_rerank_score
                result['normalized_rerank_score'] = normalized_rerank_score
                result['combined_score'] = combined_score
                result['retrieval_stage'] = 'cross_encoder_reranked'
                # Preserve source information
                if 'source' not in result:
                    result['source'] = 'Pinecone'
            
            # Sort by combined score
            reranked_results = sorted(initial_results, key=lambda x: x['combined_score'], reverse=True)
            
            # Return top-k results
            return reranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in cross-encoder reranking: {str(e)}")
            return initial_results[:top_k]

    # ------------------------------------------------------------------
    # Result post-processing helpers
    # ------------------------------------------------------------------

    def _find_exact_case_match(self, case_title_hint: str) -> List[Dict[str, Any]]:
        """
        Find exact case number match from database.
        This is called BEFORE semantic search to prioritize exact matches.
        
        Args:
            case_title_hint: Extracted case title/number from query (e.g., "T.A. 2/2023 Civil (SB)")
            
        Returns:
            List of results matching the exact case number, formatted for RAG pipeline
        """
        try:
            from apps.cases.models import Case
            
            hint_clean = case_title_hint.strip()
            exact_cases = None
            
            # Strategy 1: Try exact case-insensitive match
            exact_cases = Case.objects.filter(case_number__iexact=hint_clean)
            if exact_cases.exists():
                logger.info(f"Found exact match (iexact) for: {hint_clean}")
            else:
                # Strategy 2: Try normalized match (remove extra spaces, normalize punctuation)
                # Normalize: remove extra spaces, normalize dots and slashes
                normalized_hint = re.sub(r'\s+', ' ', hint_clean.upper())
                normalized_hint = re.sub(r'\.\s*', '.', normalized_hint)  # "T. A." -> "T.A."
                normalized_hint = re.sub(r'\s*/\s*', '/', normalized_hint)  # "2 / 2023" -> "2/2023"
                
                # Try contains with normalized version
                exact_cases = Case.objects.filter(case_number__icontains=normalized_hint)
                if exact_cases.exists():
                    logger.info(f"Found match (normalized contains) for: {hint_clean} -> {normalized_hint}")
                else:
                    # Strategy 3: Try extracting just the case number part (e.g., "T.A. 2/2023" from "T.A. 2/2023 Civil (SB)")
                    # Extract pattern like "T.A. 2/2023" or "TA 2/2023"
                    case_num_pattern = re.search(r'([A-Z]+\.?\s*\d+/\d+)', hint_clean.upper())
                    if case_num_pattern:
                        case_num_only = case_num_pattern.group(1)
                        case_num_only = re.sub(r'\s+', ' ', case_num_only)  # Normalize spaces
                        exact_cases = Case.objects.filter(case_number__icontains=case_num_only)
                        if exact_cases.exists():
                            logger.info(f"Found match (case number pattern) for: {hint_clean} -> {case_num_only}")
            
            # Strategy 4: If still no match, try matching against case_title field
            if not exact_cases or not exact_cases.exists():
                exact_cases = Case.objects.filter(case_title__icontains=hint_clean)
                if exact_cases.exists():
                    logger.info(f"Found match (case_title contains) for: {hint_clean}")
            
            if not exact_cases or not exact_cases.exists():
                logger.warning(f"No exact case match found for: {hint_clean} (tried exact, normalized, pattern, and case_title)")
                return []
            
            # Convert to RAG result format
            results = []
            # Prefer UnifiedCaseView if available for richer fields
            unified_model = None
            try:
                from apps.cases.models import UnifiedCaseView  # type: ignore
                unified_model = UnifiedCaseView
            except Exception:
                unified_model = None

            if unified_model:
                # Map Case ids to unified records when possible; else fallback to Case/CaseDetail
                for case in exact_cases[:5]:
                    try:
                        u = unified_model.objects.filter(case_id=case.id).first()
                    except Exception:
                        u = None
                    if u:
                        meta = getattr(u, 'case_metadata', {}) or {}
                        parts = [f"Case Number: {getattr(u,'case_number',case.case_number)}"]
                        title = self._get_meta_value(meta, ['case_title']) or getattr(u, 'case_title', None) or case.case_title
                        court_name = self._get_meta_value(meta, ['court','court_name']) or getattr(u, 'court', None) or (case.court.name if case.court else None)
                        if title: parts.append(f"Case Title: {title}")
                        if court_name: parts.append(f"Court: {court_name}")
                        status = self._get_meta_value(meta, ['status','case_status']) or getattr(u, 'status', None) or case.status
                        if status: parts.append(f"Status: {status}")
                        bench = self._get_meta_value(meta, ['bench','before_bench']) or getattr(u, 'bench', None) or case.bench
                        if bench: parts.append(f"Bench: {bench}")
                        sr = self._get_meta_value(meta, ['sr_number','sr no','sr'])
                        if sr: parts.append(f"SR Number: {sr}")
                        inst = self._get_meta_value(meta, ['institution_date','institution'])
                        if inst: parts.append(f"Institution Date: {inst}")
                        hearing = self._get_meta_value(meta, ['hearing_date','next_hearing','last_hearing']) or getattr(u, 'hearing_date', None)
                        if hearing: parts.append(f"Hearing Date: {hearing}")
                        short_order = self._get_meta_value(meta, ['short_order','court_order','order']) or getattr(u, 'short_order', None)
                        if short_order: parts.append(f"Short Order: {short_order}")
                        desc = self._get_meta_value(meta, ['case_description','description','summary']) or getattr(u,'case_description',None)
                        if desc: parts.append(f"Case Description: {desc}")
                        fir_no = self._get_meta_value(meta, ['fir_number','fir no'])
                        fir_date = self._get_meta_value(meta, ['fir_date','date of fir'])
                        ps = self._get_meta_value(meta, ['police_station','p.s.','police station'])
                        sections = self._get_meta_value(meta, ['sections','under section','under sections'])
                        if fir_no or fir_date or ps or sections:
                            fir_line = []
                            if fir_no: fir_line.append(f"FIR No. {fir_no}")
                            if fir_date: fir_line.append(str(fir_date))
                            if ps: fir_line.append(str(ps))
                            if sections: fir_line.append(f"Under Sections {sections}")
                            parts.append("; ".join(fir_line))
                        pet = self._get_meta_value(meta, ['advocates_petitioner','petitioners advocates','petitioner advocates',"petitioner's advocates"])
                        res = self._get_meta_value(meta, ['advocates_respondent','respondents advocates','respondent advocates',"respondent's advocates"])
                        if pet: parts.append(f"Petitioner's Advocates: {pet}")
                        if res: parts.append(f"Respondent's Advocates: {res}")
                        text = "\n".join(parts)
                        results.append({
                            'id': str(case.id),
                            'case_id': case.id,
                            'text': text,
                            'metadata': {
                                'case_id': case.id,
                                'case_number': getattr(u,'case_number',case.case_number),
                                'case_title': title,
                                'court': court_name,
                                'status': status,
                                'match_type': 'exact_case_number',
                                'advocates_petitioner': pet,
                                'advocates_respondent': res,
                                'case_description': desc,
                                'case_stage': self._get_meta_value(meta, ['case_stage','stage']),
                                'short_order': short_order,
                                'bench': bench,
                                'sr_number': sr,
                                'institution_date': inst,
                                'hearing_date': hearing,
                                'fir_number': fir_no,
                                'fir_date': fir_date,
                                'police_station': ps,
                                'under_section': sections,
                            },
                            'score': 1.0,
                        })
                    else:
                        # Fallback to Case/CaseDetail for this record
                        results.extend(self._build_case_result_from_case(case))
            else:
                # Unified view not available; use Case/CaseDetail
                exact_cases = exact_cases.select_related('case_detail', 'court')[:5]
                for case in exact_cases:
                    results.extend(self._build_case_result_from_case(case))
            
            logger.info(f"Found {len(results)} exact case match(es) for: {case_title_hint}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding exact case match: {str(e)}")
            return []
    
    def get_case_by_id(self, case_id: int) -> List[Dict[str, Any]]:
        """
        Fetch a single case by ID and format as retrieval result.
        Used to lock follow-up answers to the active case context.
        """
        try:
            from apps.cases.models import Case, CaseDetail
            case = Case.objects.select_related('court').filter(id=case_id).first()
            if not case:
                return []
            # Prefer UnifiedCaseView if available
            unified_model = None
            try:
                from apps.cases.models import UnifiedCaseView  # type: ignore
                unified_model = UnifiedCaseView
            except Exception:
                unified_model = None
            if unified_model:
                try:
                    u = unified_model.objects.filter(case_id=case.id).first()
                except Exception:
                    u = None
                if u:
                    meta = getattr(u, 'case_metadata', {}) or {}
                    parts = [f"Case Number: {getattr(u,'case_number',case.case_number)}"]
                    title = self._get_meta_value(meta, ['case_title']) or getattr(u, 'case_title', None) or case.case_title
                    court_name = self._get_meta_value(meta, ['court','court_name']) or getattr(u, 'court', None) or (case.court.name if case.court else None)
                    if title: parts.append(f"Case Title: {title}")
                    if court_name: parts.append(f"Court: {court_name}")
                    status = self._get_meta_value(meta, ['status','case_status']) or getattr(u, 'status', None) or case.status
                    if status: parts.append(f"Status: {status}")
                    bench = self._get_meta_value(meta, ['bench','before_bench']) or getattr(u, 'bench', None) or case.bench
                    if bench: parts.append(f"Bench: {bench}")
                    sr = self._get_meta_value(meta, ['sr_number','sr no','sr'])
                    if sr: parts.append(f"SR Number: {sr}")
                    inst = self._get_meta_value(meta, ['institution_date','institution'])
                    if inst: parts.append(f"Institution Date: {inst}")
                    hearing = self._get_meta_value(meta, ['hearing_date','next_hearing','last_hearing']) or getattr(u,'hearing_date',None)
                    if hearing: parts.append(f"Hearing Date: {hearing}")
                    short_order = self._get_meta_value(meta, ['short_order','court_order','order']) or getattr(u,'short_order',None)
                    if short_order: parts.append(f"Short Order: {short_order}")
                    desc = self._get_meta_value(meta, ['case_description','description','summary'])
                    if desc: parts.append(f"Case Description: {desc}")
                    fir_no = self._get_meta_value(meta, ['fir_number','fir no'])
                    fir_date = self._get_meta_value(meta, ['fir_date','date of fir'])
                    ps = self._get_meta_value(meta, ['police_station','p.s.','police station'])
                    sections = self._get_meta_value(meta, ['sections','under section','under sections'])
                    if fir_no or fir_date or ps or sections:
                        fir_line = []
                        if fir_no: fir_line.append(f"FIR No. {fir_no}")
                        if fir_date: fir_line.append(str(fir_date))
                        if ps: fir_line.append(str(ps))
                        if sections: fir_line.append(f"Under Sections {sections}")
                        parts.append("; ".join(fir_line))
                    pet = self._get_meta_value(meta, ['advocates_petitioner','petitioners advocates','petitioner advocates',"petitioner's advocates"])
                    res = self._get_meta_value(meta, ['advocates_respondent','respondents advocates','respondent advocates',"respondent's advocates"])
                    if pet: parts.append(f"Petitioner's Advocates: {pet}")
                    if res: parts.append(f"Respondent's Advocates: {res}")
                    text = "\n".join(parts)
                    return [{
                        'id': str(case.id),
                        'case_id': case.id,
                        'text': text,
                        'metadata': {
                            'case_id': case.id,
                            'case_number': getattr(u,'case_number',case.case_number),
                            'case_title': title,
                            'court': court_name,
                            'status': status,
                            'match_type': 'by_case_id',
                            'advocates_petitioner': pet,
                            'advocates_respondent': res,
                            'case_description': desc,
                            'case_stage': self._get_meta_value(meta, ['case_stage','stage']),
                            'short_order': short_order,
                            'bench': bench,
                            'sr_number': sr,
                            'institution_date': inst,
                            'hearing_date': hearing,
                            'fir_number': fir_no,
                            'fir_date': fir_date,
                            'police_station': ps,
                            'under_section': sections,
                        },
                        'score': 1.0,
                        'qa_rank': 1,
                        'qa_relevance_score': 1.0,
                        'retrieval_method': 'active_case_lock',
                    }]
            # Try fetch details
            try:
                case_detail = CaseDetail.objects.get(case_id=case.id)
            except CaseDetail.DoesNotExist:
                case_detail = None

            parts = [f"Case Number: {case.case_number}"]
            if case.case_title:
                parts.append(f"Case Title: {case.case_title}")
            if case.court:
                parts.append(f"Court: {case.court.name}")
            if case.status:
                parts.append(f"Status: {case.status}")
            if case_detail:
                if case_detail.advocates_petitioner:
                    parts.append(f"Petitioner's Advocates: {case_detail.advocates_petitioner}")
                if case_detail.advocates_respondent:
                    parts.append(f"Respondent's Advocates: {case_detail.advocates_respondent}")
                if case_detail.case_description:
                    parts.append(f"Case Description: {case_detail.case_description}")
                if case_detail.case_stage:
                    parts.append(f"Case Stage: {case_detail.case_stage}")
                if case_detail.short_order:
                    parts.append(f"Short Order: {case_detail.short_order}")
                if case_detail.before_bench:
                    parts.append(f"Bench: {case_detail.before_bench}")

            text = "\n".join(parts)
            return [{
                'id': str(case.id),
                'case_id': case.id,
                'text': text,
                'metadata': {
                    'case_id': case.id,
                    'case_number': case.case_number,
                    'case_title': case.case_title,
                    'court': case.court.name if case.court else None,
                    'status': case.status,
                    'match_type': 'by_case_id',
                    'advocates_petitioner': case_detail.advocates_petitioner if case_detail else None,
                    'advocates_respondent': case_detail.advocates_respondent if case_detail else None,
                    'case_description': case_detail.case_description if case_detail else None,
                    'case_stage': case_detail.case_stage if case_detail else None,
                    'short_order': case_detail.short_order if case_detail else None,
                    'bench': case_detail.before_bench if case_detail else None,
                },
                'score': 1.0,
                'qa_rank': 1,
                'qa_relevance_score': 1.0,
                'retrieval_method': 'active_case_lock',
            }]
        except Exception as e:
            logger.error(f"Error fetching case by id {case_id}: {e}")
            return []

    def _build_case_result_from_case(self, case) -> List[Dict[str, Any]]:
        """Fallback builder using Case and CaseDetail when UnifiedCaseView is not available."""
        try:
            from apps.cases.models import CaseDetail
        except Exception:
            CaseDetail = None  # type: ignore
        case_detail = None
        if CaseDetail:
            try:
                case_detail = CaseDetail.objects.get(case_id=case.id)
            except Exception:
                case_detail = None

        parts = [f"Case Number: {case.case_number}"]
        if case.case_title:
            parts.append(f"Case Title: {case.case_title}")
        if getattr(case, 'court', None):
            parts.append(f"Court: {case.court.name}")
        if getattr(case, 'status', None):
            parts.append(f"Status: {case.status}")
        if case_detail:
            if case_detail.advocates_petitioner:
                parts.append(f"Petitioner's Advocates: {case_detail.advocates_petitioner}")
            if case_detail.advocates_respondent:
                parts.append(f"Respondent's Advocates: {case_detail.advocates_respondent}")
            if case_detail.case_description:
                parts.append(f"Case Description: {case_detail.case_description}")
            if case_detail.case_stage:
                parts.append(f"Case Stage: {case_detail.case_stage}")
            if case_detail.short_order:
                parts.append(f"Short Order: {case_detail.short_order}")
            if case_detail.before_bench:
                parts.append(f"Bench: {case_detail.before_bench}")
        text = "\n".join(parts)
        return [{
            'id': str(case.id),
            'case_id': case.id,
            'text': text,
            'metadata': {
                'case_id': case.id,
                'case_number': case.case_number,
                'case_title': case.case_title,
                'court': case.court.name if getattr(case, 'court', None) else None,
                'status': getattr(case, 'status', None),
                'match_type': 'exact_case_number',
                'advocates_petitioner': case_detail.advocates_petitioner if case_detail else None,
                'advocates_respondent': case_detail.advocates_respondent if case_detail else None,
                'case_description': case_detail.case_description if case_detail else None,
                'case_stage': case_detail.case_stage if case_detail else None,
                'short_order': case_detail.short_order if case_detail else None,
                'bench': case_detail.before_bench if case_detail else getattr(case, 'bench', None),
            },
            'score': 1.0,
        }]
    
    def _extract_case_title_from_question(self, question: str) -> Optional[str]:
        if not question:
            return None

        lowered = question.lower()
        # 1) Heuristic markers common in our UI phrasing
        patterns = [
            (" recorded for ", None),
            (" linked to ", None),
            (" sections was ", " filed"),
            (" heard ", None),
            (" case status for ", None),
            (" short order in ", None),
            (" advocates involved in ", None),  # Fixed: was "advocates in", now handles "involved in"
            (" advocates in ", None),  # Keep for backward compatibility
            (" petitioner's advocates in ", None),  # Handle "petitioner's advocates in"
            (" respondent's advocates in ", None),  # Handle "respondent's advocates in"
            (" fir number for ", None),
            (" fir date for ", None),
            (" police station is linked to ", None),
            (" orders recorded for ", None),
            (" under which sections was ", " filed"),
            # Newly added generic markers the user uses:
            (" details for this case:", None),
            (" details for this case ", None),
            (" details for ", None),
            (" about case ", None),
            (" regarding case ", None),
        ]

        for marker, end_marker in patterns:
            idx = lowered.find(marker)
            if idx == -1:
                continue

            start = idx + len(marker)
            end = len(question)
            if end_marker:
                end_idx = lowered.find(end_marker, start)
                if end_idx != -1:
                    end = end_idx

            case_title = question[start:end].strip().strip('"\' ?.')
            if case_title:
                return case_title

        # 2) Regex for case numbers like "Crl. Misc. 2/2025 Bail After Arrest (SB)"
        try:
            num_match = re.search(r'([A-Za-z. ]+?\s+\d+/\d+\s+[A-Za-z][A-Za-z ]*(?:\s*\([A-Z]+\))?)', question, flags=re.IGNORECASE)
            if num_match:
                candidate = num_match.group(1).strip()
                return candidate
        except Exception:
            pass

        # 3) Regex for titles like "Rimsa Tahir vs Pakistan Institute of Medical Sciences" (v., vs, versus)
        try:
            title_match = re.search(r'([A-Za-z][A-Za-z .]+?\s+(?:v\.|vs|versus)\s+[A-Za-z][A-Za-z .]+)', question, flags=re.IGNORECASE)
            if title_match:
                return title_match.group(1).strip()
        except Exception:
            pass

        return None

    def _filter_results_by_case_title(self, results: List[Dict[str, Any]], case_title_hint: str) -> List[Dict[str, Any]]:
        if not results or not case_title_hint:
            return results

        normalized_hint = self._normalize_case_title(case_title_hint)
        matched: List[Dict[str, Any]] = []
        deduped: List[Dict[str, Any]] = []
        seen_keys = set()

        for result in results:
            metadata = result.get('metadata', {})
            case_id = metadata.get('case_id') or result.get('case_id')
            key = None
            try:
                if case_id is not None:
                    key = int(float(case_id))
            except (TypeError, ValueError):
                key = None

            if key is None:
                key = result.get('id')

            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(result)

            candidate_title = result.get('case_title') or metadata.get('case_title')
            if candidate_title and self._normalize_case_title(candidate_title) == normalized_hint:
                matched.append(result)

        return matched if matched else deduped

    def _normalize_case_title(self, title: str) -> str:
        cleaned = re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()
        return cleaned
    
    def _apply_diversity_control(self, 
                               results: List[Dict[str, Any]], 
                               top_k: int) -> List[Dict[str, Any]]:
        """Apply Maximal Marginal Relevance (MMR) for diversity"""
        try:
            if len(results) <= 1:
                return results
            
            # Simple diversity control: avoid very similar results
            diverse_results = []
            used_texts = set()
            
            for result in results:
                text = result.get('text', '').lower()
                
                # Check for similarity with already selected results
                is_similar = False
                for used_text in used_texts:
                    # Simple similarity check (can be improved with embeddings)
                    text_words = set(text.split())
                    used_words = set(used_text.split())
                    intersection = text_words & used_words
                    union = text_words | used_words
                    
                    # Avoid division by zero
                    if len(union) > 0:
                        similarity = len(intersection) / len(union)
                        if similarity > self.config['diversity_threshold']:
                            is_similar = True
                            break
                
                if not is_similar:
                    diverse_results.append(result)
                    used_texts.add(text)
                    
                    if len(diverse_results) >= top_k:
                        break
            
            # If we don't have enough diverse results, add the best remaining ones
            if len(diverse_results) < top_k:
                for result in results:
                    if result not in diverse_results:
                        diverse_results.append(result)
                        if len(diverse_results) >= top_k:
                            break
            
            return diverse_results
            
        except Exception as e:
            logger.error(f"Error in diversity control: {str(e)}")
            return results[:top_k]
    
    def _fallback_retrieval(self, query: str, top_k: int,
                          legal_domain: Optional[str] = None,
                          case_type: Optional[str] = None,
                          court_filter: Optional[str] = None,
                          year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fallback retrieval when Pinecone is not available"""
        try:
            logger.info("Using fallback retrieval with database and embeddings")
            
            # Step 1: Try to get results from existing QA knowledge base
            qa_results = self._retrieve_from_qa_knowledge_base(
                query, top_k, legal_domain, case_type, court_filter, year_filter
            )
            if qa_results:
                logger.info(f"Fallback retrieval found {len(qa_results)} results from QA knowledge base")
                return qa_results
            
            # Step 2: Try to get results from database with embeddings
            db_results = self._retrieve_from_database_with_embeddings(
                query, top_k, legal_domain, case_type, court_filter, year_filter
            )
            if db_results:
                logger.info(f"Fallback retrieval found {len(db_results)} results from database")
                return db_results
            
            # Step 3: Try simple database search as last resort
            simple_results = self._retrieve_from_database_simple(
                query, top_k, legal_domain, case_type, court_filter, year_filter
            )
            if simple_results:
                logger.info(f"Fallback retrieval found {len(simple_results)} results from simple database search")
                return simple_results
            
            logger.warning("Fallback retrieval found no results")
            return []
            
        except Exception as e:
            logger.error(f"Error in fallback retrieval: {str(e)}")
            return []
    
    def _retrieve_from_qa_knowledge_base(self, query: str, top_k: int, 
                                       legal_domain: Optional[str] = None,
                                       case_type: Optional[str] = None,
                                       court_filter: Optional[str] = None,
                                       year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve from existing QA knowledge base with filters"""
        try:
            from qa_app.models import QAKnowledgeBase
            
            # Build filter conditions using correct field names
            filters = {'content_text__icontains': query}
            
            if legal_domain:
                filters['legal_domain'] = legal_domain
            if court_filter:
                filters['court'] = court_filter
            if year_filter:
                filters['date_decided__year'] = year_filter
            
            # Search in QA knowledge base with filters
            qa_docs = QAKnowledgeBase.objects.filter(**filters).order_by('-legal_relevance_score')[:top_k]
            
            results = []
            if qa_docs and self.embedding_model:
                # OPTIMIZATION: Batch embedding generation for QA docs
                import time
                batch_start = time.time()
                
                # Prepare texts for batch embedding
                texts_for_embedding = [doc.content_text[:1000] for doc in qa_docs]
                
                # Generate query embedding
                query_embedding = self.embedding_model.encode([query])[0]
                
                # Generate all document embeddings in one batch with caching
                doc_embeddings = self._get_embeddings_with_cache(texts_for_embedding)
                
                # Vectorized similarity calculation
                query_norm = np.linalg.norm(query_embedding)
                doc_norms = np.linalg.norm(doc_embeddings, axis=1)
                similarities = np.dot(doc_embeddings, query_embedding) / (doc_norms * query_norm)
                
                batch_time = time.time() - batch_start
                logger.info(f"QA KB batch embedding time: {batch_time:.3f}s ({len(qa_docs)} documents)")
                
                # Build results with pre-calculated similarities
                for i, doc in enumerate(qa_docs):
                    result = {
                        'id': f"qa_doc_{doc.id}",
                        'score': float(similarities[i]),
                        'text': doc.content_text,
                        'metadata': {
                            'source': 'qa_knowledge_base',
                            'legal_domain': doc.legal_domain,
                            'source_type': doc.source_type,
                            'court': doc.court,
                            'year': doc.date_decided.year if doc.date_decided else None,
                            'legal_relevance_score': doc.legal_relevance_score,
                            'citations': doc.citations,
                            'content_quality_score': doc.content_quality_score
                        },
                        'retrieval_stage': 'fallback_qa_kb',
                        'structured_data': self._entities_to_structured(doc.legal_entities)
                    }
                    results.append(result)
            else:
                # Fallback for when embedding model is not available
                for doc in qa_docs:
                    result = {
                        'id': f"qa_doc_{doc.id}",
                        'score': 0.5,  # Default score
                        'text': doc.content_text,
                        'metadata': {
                            'source': 'qa_knowledge_base',
                            'legal_domain': doc.legal_domain,
                            'source_type': doc.source_type,
                            'court': doc.court,
                            'year': doc.date_decided.year if doc.date_decided else None,
                            'legal_relevance_score': doc.legal_relevance_score,
                            'citations': doc.citations,
                            'content_quality_score': doc.content_quality_score
                        },
                        'retrieval_stage': 'fallback_qa_kb',
                        'structured_data': self._entities_to_structured(doc.legal_entities)
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving from QA knowledge base: {str(e)}")
            return []
    
    def _retrieve_from_database_with_embeddings(self, query: str, top_k: int,
                                              legal_domain: Optional[str] = None,
                                              case_type: Optional[str] = None,
                                              court_filter: Optional[str] = None,
                                              year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve from database with embedding similarity and filters - OPTIMIZED"""
        try:
            from django.db import connection
            import time
            
            start_time = time.time()
            
            # Build SQL query with filters
            where_conditions = ["dt.clean_text IS NOT NULL", "LENGTH(dt.clean_text) > 100"]
            params = []
            
            if legal_domain:
                where_conditions.append("legal_domain = %s")
                params.append(legal_domain)
            if case_type:
                where_conditions.append("case_type = %s")
                params.append(case_type)
            if court_filter:
                where_conditions.append("court = %s")
                params.append(court_filter)
            if year_filter:
                where_conditions.append("year = %s")
                params.append(year_filter)
            
            sql = f"""
                SELECT dt.id, dt.clean_text, d.file_name
                FROM document_texts dt
                JOIN documents d ON dt.document_id = d.id
                WHERE {' AND '.join(where_conditions)}
                LIMIT 100
            """
            
            # Get documents from database
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            
            if not rows:
                return []
            
            db_time = time.time() - start_time
            logger.info(f"Database query time: {db_time:.3f}s")
            
            # Generate query embedding
            if not self.embedding_model:
                return []
            
            embedding_start = time.time()
            query_embedding = self.embedding_model.encode([query])[0]
            query_embedding_time = time.time() - embedding_start
            logger.info(f"Query embedding time: {query_embedding_time:.3f}s")
            
            # OPTIMIZATION 1: Batch embedding generation
            batch_start = time.time()
            texts_for_embedding = [row[1][:1000] for row in rows]  # Limit text for embedding
            
            # Generate all document embeddings in one batch with caching
            doc_embeddings = self._get_embeddings_with_cache(texts_for_embedding)
            batch_time = time.time() - batch_start
            logger.info(f"Batch embedding generation time: {batch_time:.3f}s ({len(texts_for_embedding)} documents)")
            
            # OPTIMIZATION 2: Vectorized similarity calculation
            similarity_start = time.time()
            query_norm = np.linalg.norm(query_embedding)
            doc_norms = np.linalg.norm(doc_embeddings, axis=1)
            
            # Calculate all similarities at once
            similarities = np.dot(doc_embeddings, query_embedding) / (doc_norms * query_norm)
            similarity_time = time.time() - similarity_start
            logger.info(f"Vectorized similarity calculation time: {similarity_time:.3f}s")
            
            # Build results
            results = []
            for i, row in enumerate(rows):
                doc_id, text, file_name = row
                
                result = {
                    'id': f"db_doc_{doc_id}",
                    'score': float(similarities[i]),
                    'text': text[:2000],  # Limit text for results
                    'metadata': {
                        'source': 'database',
                        'file_name': file_name,
                        'document_id': doc_id
                    },
                    'retrieval_stage': 'fallback_db_embedding'
                }
                results.append(result)
            
            # Sort by similarity and return top-k
            results.sort(key=lambda x: x['score'], reverse=True)
            
            total_time = time.time() - start_time
            logger.info(f"Total optimized embedding retrieval time: {total_time:.3f}s")
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving from database with embeddings: {str(e)}")
            return []
    
    def _retrieve_from_database_simple(self, query: str, top_k: int,
                                      legal_domain: Optional[str] = None,
                                      case_type: Optional[str] = None,
                                      court_filter: Optional[str] = None,
                                      year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Simple database search as last resort with filters"""
        try:
            from django.db import connection
            
            # Build filter conditions
            where_conditions = ["(case_text ILIKE %s OR case_title ILIKE %s)"]
            params = [f'%{query}%', f'%{query}%']
            
            if legal_domain:
                where_conditions.append("legal_domain = %s")
                params.append(legal_domain)
            if case_type:
                where_conditions.append("case_type = %s")
                params.append(case_type)
            if court_filter:
                where_conditions.append("court = %s")
                params.append(court_filter)
            if year_filter:
                where_conditions.append("year = %s")
                params.append(year_filter)
            
            # Add ordering and limit parameters
            params.extend([f'%{query}%', f'%{query}%', top_k])
            
            sql = f"""
                SELECT dt.id, dt.clean_text, d.file_name
                FROM document_texts dt
                JOIN documents d ON dt.document_id = d.id
                WHERE dt.clean_text ILIKE %s OR d.file_name ILIKE %s
                ORDER BY 
                    CASE 
                        WHEN dt.clean_text ILIKE %s THEN 1
                        WHEN d.file_name ILIKE %s THEN 2
                        ELSE 3
                    END
                LIMIT %s
            """
            
            # Simple text search in database
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            
            results = []
            for row in rows:
                doc_id, text, file_name = row
                
                # Simple relevance scoring based on text match
                text_lower = text.lower() if text else ""
                query_lower = query.lower()
                match_count = text_lower.count(query_lower)
                relevance_score = min(match_count / 10.0, 1.0)  # Normalize to 0-1
                
                result = {
                    'id': f"db_simple_{doc_id}",
                    'score': relevance_score,
                    'text': text[:2000] if text else "",
                    'metadata': {
                        'source': 'database_simple',
                        'file_name': file_name,
                        'document_id': doc_id,
                        'match_count': match_count
                    },
                    'retrieval_stage': 'fallback_db_simple'
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in simple database retrieval: {str(e)}")
            return []
    
    def get_qa_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about QA retrieval performance"""
        return {
            'embedding_model_loaded': self.embedding_model is not None,
            'cross_encoder_loaded': self.cross_encoder is not None,
            'pinecone_connected': self.pinecone_index is not None,
            'embedding_dimension': self.embedding_dimension,
            'config': self.config,
            'retrieval_method': 'two_stage_qa_retrieval'
        }

    def _format_structured_snippet(self, structured_data: Dict[str, Any]) -> str:
        """Convert structured metadata into a concise natural-language snippet."""
        if not structured_data:
            return ""

        parts: List[str] = []

        def _join(value: Any) -> str:
            if value is None:
                return ''
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return ", ".join([_join(item) for item in value if item])
            if isinstance(value, dict):
                return ", ".join([f"{k.replace('_', ' ').title()}: {_join(v)}" for k, v in value.items() if v])
            return str(value)

        if structured_data.get('advocates_petitioner'):
            parts.append(f"Petitioner Advocates: {_join(structured_data['advocates_petitioner'])}")
        if structured_data.get('advocates_respondent'):
            parts.append(f"Respondent Advocates: {_join(structured_data['advocates_respondent'])}")
        if structured_data.get('bench'):
            parts.append(f"Bench: {_join(structured_data['bench'])}")
        if structured_data.get('court'):
            parts.append(f"Court: {_join(structured_data['court'])}")
        if structured_data.get('status'):
            parts.append(f"Case Status: {_join(structured_data['status'])}")
        if structured_data.get('short_order'):
            parts.append(f"Short Order: {_join(structured_data['short_order'])}")
        if structured_data.get('fir_number'):
            parts.append(f"FIR Number: {_join(structured_data['fir_number'])}")

        if not parts:
            # Fallback to summarizing any other keys
            for key, value in structured_data.items():
                if key in {'advocates_petitioner', 'advocates_respondent', 'bench', 'court', 'status', 'short_order', 'fir_number'}:
                    continue
                rendered = _join(value)
                if rendered:
                    parts.append(f"{key.replace('_', ' ').title()}: {rendered}")

        return " | ".join(parts)
