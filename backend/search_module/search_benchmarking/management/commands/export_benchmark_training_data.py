import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch, Q

from search_benchmarking.models import BenchmarkExecution, BenchmarkQuery, BenchmarkQuerySet, BenchmarkResult
from apps.cases.models import Case, CaseSearchProfile


class Command(BaseCommand):
    """
    Export benchmark search results into a training dataset for learned rerankers.

    The command emits one record per (query, candidate case) containing:
      - query metadata (text, type, difficulty, domain, query-set info)
      - candidate metadata (rank position, score, case attributes, profile summaries/tags)
      - gold label (1 if case is among expected results, else 0)

    Default output is newline-delimited JSON (JSONL) for easy downstream ingestion.
    """

    help = "Export benchmark results to a JSONL dataset for training a reranker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            required=True,
            help="Path to write the training dataset (JSONL).",
        )
        parser.add_argument(
            "--execution-ids",
            type=str,
            help="Comma-separated list of BenchmarkExecution IDs to include.",
        )
        parser.add_argument(
            "--query-set-id",
            type=int,
            help="Limit export to a specific BenchmarkQuerySet ID.",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=50,
            help="Maximum number of ranked candidates per query to export (default: 50).",
        )
        parser.add_argument(
            "--include-errors",
            action="store_true",
            help="Include results with non-success statuses (default: success only).",
        )
        parser.add_argument(
            "--min-label",
            type=int,
            choices=[0, 1],
            default=0,
            help="Minimum label to export (use 1 to keep positives only).",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"]).expanduser()
        execution_ids = self._parse_execution_ids(options.get("execution_ids"))
        query_set_id = options.get("query_set_id")
        top_k: int = options["top_k"]
        include_errors: bool = options["include_errors"]
        min_label: int = options["min_label"]

        if top_k <= 0:
            raise CommandError("--top-k must be a positive integer.")

        queryset = BenchmarkResult.objects.select_related(
            "execution", "execution__query_set", "query"
        )

        if execution_ids:
            queryset = queryset.filter(execution_id__in=execution_ids)
        if query_set_id:
            queryset = queryset.filter(execution__query_set_id=query_set_id)
        if not include_errors:
            queryset = queryset.filter(status="success")

        queryset = queryset.order_by("execution_id", "query_id")

        if not queryset.exists():
            raise CommandError("No benchmark results matched the provided filters.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        records_written = 0
        query_count = 0

        profile_cache: Dict[int, Optional[CaseSearchProfile]] = {}
        case_cache: Dict[int, Optional[Case]] = {}

        with output_path.open("w", encoding="utf-8") as fh:
            for result in queryset.iterator():
                query = result.query
                expected_case_ids, expected_relevance = self._extract_expected_cases(query)

                returned_candidates = (result.returned_results or [])[:top_k]
                if not returned_candidates:
                    continue

                query_payload = self._build_query_payload(result, query)

                for rank_idx, candidate in enumerate(returned_candidates, start=1):
                    case_id = candidate.get("case_id")
                    if not case_id:
                        continue

                    label = 1 if case_id in expected_case_ids else 0
                    if label < min_label:
                        continue

                    case_payload = self._build_case_payload(
                        case_id,
                        candidate,
                        profile_cache,
                        case_cache,
                        expected_relevance,
                    )

                    record = {
                        **query_payload,
                        **case_payload,
                        "rank_position": rank_idx,
                        "result_score": candidate.get("score"),
                        "label": label,
                    }

                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    records_written += 1

                query_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {records_written} training records from {query_count} benchmark queries to {output_path}"
            )
        )

    def _parse_execution_ids(self, raw: Optional[str]) -> Optional[List[int]]:
        if not raw:
            return None
        ids = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                ids.append(int(token))
            except ValueError:
                raise CommandError(f"Invalid execution id: {token}")
        return ids or None

    def _extract_expected_cases(self, query: BenchmarkQuery) -> (Set[int], Dict[int, float]):
        expected_ids: Set[int] = set()
        relevance_map: Dict[int, float] = {}
        raw_expected = query.expected_results or []

        for item in raw_expected:
            if isinstance(item, dict):
                case_id = item.get("case_id") or item.get("id")
                if case_id:
                    expected_ids.add(case_id)
                    relevance_map[case_id] = float(item.get("score", item.get("relevance", 1.0)))
            else:
                try:
                    case_id = int(item)
                    expected_ids.add(case_id)
                    relevance_map.setdefault(case_id, 1.0)
                except (TypeError, ValueError):
                    continue

        return expected_ids, relevance_map

    def _build_query_payload(self, result: BenchmarkResult, query: BenchmarkQuery) -> Dict[str, Optional[str]]:
        execution = result.execution
        query_set = execution.query_set
        return {
            "execution_id": execution.id,
            "execution_name": execution.execution_name,
            "execution_started_at": execution.started_at.isoformat() if execution.started_at else None,
            "query_set_id": query_set.id if query_set else None,
            "query_set_name": query_set.name if query_set else None,
            "query_set_category": query_set.category if query_set else None,
            "query_id": query.id,
            "query_text": query.query_text,
            "query_type": query.query_type,
            "query_difficulty": query.difficulty_level,
            "query_legal_domain": query.legal_domain,
            "search_mode": result.search_mode,
            "ranking_algorithm": result.ranking_algorithm,
            "precision_at_10": result.precision_at_10,
            "recall_at_10": result.recall_at_10,
            "mrr": result.mrr,
            "ndcg_at_10": result.ndcg_at_10,
        }

    def _build_case_payload(
        self,
        case_id: int,
        candidate: Dict,
        profile_cache: Dict[int, Optional[CaseSearchProfile]],
        case_cache: Dict[int, Optional[Case]],
        expected_relevance: Dict[int, float],
    ) -> Dict[str, Optional[str]]:
        profile = self._get_case_profile(case_id, profile_cache)
        case_obj = self._get_case(case_id, case_cache)

        metadata = profile.metadata if profile and isinstance(profile.metadata, dict) else {}
        abstract_sentences = metadata.get("abstract_sentences", []) if metadata else []
        abstract_text = ""
        if metadata:
            abstract_text = metadata.get("abstract_text") or " ".join(abstract_sentences)

        return {
            "case_id": case_id,
            "case_number": candidate.get("case_number") or (case_obj.case_number if case_obj else None),
            "case_title": candidate.get("case_title") or (case_obj.case_title if case_obj else None),
            "case_court": candidate.get("court") or (case_obj.court.name if case_obj and case_obj.court else None),
            "case_status": getattr(case_obj, "status", None) if case_obj else None,
            "case_bench": getattr(case_obj, "bench", None) if case_obj else None,
            "case_subject_tags": profile.subject_tags if profile else [],
            "case_section_tags": profile.section_tags if profile else [],
            "case_summary": profile.summary_text if profile else "",
            "case_metadata": metadata,
            "case_abstract": abstract_text,
            "expected_relevance_score": expected_relevance.get(case_id),
        }

    def _get_case_profile(
        self, case_id: int, cache: Dict[int, Optional[CaseSearchProfile]]
    ) -> Optional[CaseSearchProfile]:
        if case_id in cache:
            return cache[case_id]
        profile = (
            CaseSearchProfile.objects.select_related("case")
            .filter(case_id=case_id)
            .first()
        )
        cache[case_id] = profile
        return profile

    def _get_case(self, case_id: int, cache: Dict[int, Optional[Case]]) -> Optional[Case]:
        if case_id in cache:
            return cache[case_id]
        case_obj = (
            Case.objects.select_related("court")
            .only(
                "id",
                "case_number",
                "case_title",
                "status",
                "bench",
                "court__name",
            )
            .filter(id=case_id)
            .first()
        )
        cache[case_id] = case_obj
        return case_obj

