"""
Learned reranker service
Provides cross-encoder based reranking for top-N search results.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from django.conf import settings

try:
    from sentence_transformers import CrossEncoder
except ImportError:  # pragma: no cover - optional dependency
    CrossEncoder = None  # type: ignore

from apps.cases.models import CaseSearchProfile

logger = logging.getLogger(__name__)


class LearnedReranker:
    """Thin wrapper around a sentence-transformers CrossEncoder for reranking."""

    def __init__(self, model_path: str | Path, config: Optional[Dict[str, Any]] = None):
        if CrossEncoder is None:
            raise RuntimeError(
                "sentence-transformers is not installed; unable to initialize LearnedReranker."
            )

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Learned reranker model not found at {self.model_path}")

        self.config = config or {}
        self.batch_size: int = int(self.config.get("learned_reranker_batch_size", 32))
        self.blend_weight: float = float(self.config.get("learned_reranker_blend_weight", 0.6))
        self.max_candidates: int = int(self.config.get("learned_reranker_max_candidates", 50))

        logger.info("Loading learned reranker model from %s", self.model_path)
        self.model = CrossEncoder(str(self.model_path), max_length=self.config.get("learned_reranker_max_length", 512))

        self._profile_cache: Dict[int, Optional[CaseSearchProfile]] = {}

    def rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        query_analysis: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Reorder the provided results using the learned reranker.

        Args:
            query: Original query string.
            results: List of search result dictionaries (must include case_id).
            query_analysis: Optional query metadata (unused for now, kept for future features).
            top_k: Optional limit on the number of results to score; defaults to configured max.
        """
        if not results or len(results) <= 1:
            return results

        limit = min(top_k or len(results), self.max_candidates, len(results))
        candidates = results[:limit]

        model_inputs: List[List[str]] = []
        for result in candidates:
            case_text = self._build_candidate_text(result)
            if not case_text:
                case_text = result.get("case_title") or ""
            model_inputs.append(
                [
                    f"Query: {query}",
                    f"Candidate: {case_text}",
                ]
            )

        if not model_inputs:
            return results

        scores = self.model.predict(model_inputs, batch_size=self.batch_size, show_progress_bar=False)

        for result, score in zip(candidates, scores):
            base_score = (
                result.get("final_rerank_score")
                or result.get("final_score")
                or result.get("combined_score")
                or 0.0
            )
            blended = (1.0 - self.blend_weight) * base_score + self.blend_weight * float(score)

            result["learned_reranker_score"] = float(score)
            result["final_score"] = blended
            result["final_rerank_score"] = blended

        reranked = sorted(results, key=lambda item: item.get("final_rerank_score", item.get("final_score", 0)), reverse=True)
        return reranked

    def _build_candidate_text(self, result: Dict[str, Any]) -> str:
        """Compose a textual representation for the candidate case."""
        case_id = result.get("case_id")
        profile = self._get_profile(case_id)

        parts: List[str] = []
        case_title = result.get("case_title") or (profile.case.case_title if profile and profile.case else None)
        case_number = result.get("case_number") or (profile.case.case_number if profile and profile.case else None)
        court = result.get("court") or (profile.case.court.name if profile and profile.case and profile.case.court else None)
        status = result.get("status") or (profile.case.status if profile and profile.case else None)

        if case_title:
            parts.append(f"Title: {case_title}")
        if case_number:
            parts.append(f"Case Number: {case_number}")
        if court:
            parts.append(f"Court: {court}")
        if status:
            parts.append(f"Status: {status}")

        if profile:
            if profile.summary_text:
                parts.append(f"Summary: {profile.summary_text}")
            metadata = profile.metadata or {}
            abstract = metadata.get("abstract_text")
            if abstract:
                parts.append(f"Abstract: {abstract}")
            elif metadata.get("abstract_sentences"):
                parts.append("Abstract: " + " ".join(metadata["abstract_sentences"]))

            if profile.subject_tags:
                parts.append("Subjects: " + ", ".join(profile.subject_tags[:6]))
            if profile.section_tags:
                parts.append("Sections: " + ", ".join(profile.section_tags[:6]))
            if profile.party_tokens:
                parts.append("Parties: " + ", ".join(profile.party_tokens[:6]))

        return " | ".join(parts)

    def _get_profile(self, case_id: Optional[int]) -> Optional[CaseSearchProfile]:
        if case_id is None:
            return None
        if case_id in self._profile_cache:
            return self._profile_cache[case_id]

        profile = (
            CaseSearchProfile.objects.select_related("case", "case__court")
            .filter(case_id=case_id)
            .first()
        )
        self._profile_cache[case_id] = profile
        return profile




