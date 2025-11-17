"""Evaluate chatbot retrieval and answer quality against a labelled dataset."""

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from django.conf import settings
from django.core.management.base import BaseCommand

from services.enhanced_qa_engine import EnhancedQAEngine
from qa_app.services.qa_retrieval_service import QARetrievalService


class Command(BaseCommand):
    help = "Evaluate chatbot retrieval and answer accuracy using a labelled dataset"

    DEFAULT_DATASET = Path("evaluation") / "chatbot_eval_dataset.jsonl"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            type=str,
            default=str(self.DEFAULT_DATASET),
            help="Path to the JSONL dataset produced by generate_chatbot_eval_dataset.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optionally limit the number of questions evaluated (useful for smoke tests).",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=10,
            help="Top K results to use when computing retrieval metrics.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Optional path to write per-question evaluation results (JSONL).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print per-question results to stdout.",
        )
        parser.add_argument(
            "--rag-only",
            action="store_true",
            help="Skip structured lookup so every query runs through the RAG pipeline.",
        )

    def handle(self, *args, **options):
        dataset_path = self._resolve_path(options.get("dataset"))
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found at {dataset_path}. Generate it first with generate_chatbot_eval_dataset.")

        limit = options.get("limit") or 0
        top_k = options.get("top_k") or 10
        verbose = options.get("verbose", False)
        output_path = options.get("output") or ""
        rag_only = options.get("rag_only", False)
        if output_path:
            output_path = self._resolve_path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        dataset = self._load_dataset(dataset_path, limit)
        total_questions = len(dataset)
        if not dataset:
            self.stdout.write(self.style.WARNING("Dataset is empty. Nothing to evaluate."))
            return

        self.stdout.write(f"Loaded {total_questions} evaluation questions from {dataset_path}")
        self.stdout.write("Initialising chatbot components (this may take a moment)...")

        start_time = time.time()
        engine = EnhancedQAEngine()
        retrieval_service: QARetrievalService = engine.qa_retrieval_service
        init_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Components initialised in {init_time:.2f}s"))

        if rag_only:
            def _skip_structured_answer(question: str, filters: Optional[Dict[str, Any]] = None):
                return None

            engine._attempt_structured_answer = _skip_structured_answer  # type: ignore[attr-defined]
            self.stdout.write(self.style.WARNING("Structured lookup disabled: forcing RAG-only evaluation"))

        results: List[Dict[str, Any]] = []

        for idx, row in enumerate(dataset, 1):
            question = row["question"]
            expected_answer = row["expected_answer"]
            relevant_case_ids = self._normalize_ids([row.get("relevant_case_id")])

            retrieval_start = time.time()
            retrieval_results = retrieval_service.retrieve_for_qa(question, top_k=top_k)
            retrieval_time = time.time() - retrieval_start

            retrieved_case_ids = self._extract_case_ids(retrieval_results)
            retrieval_metrics = self._compute_retrieval_metrics(relevant_case_ids, retrieved_case_ids)

            answer_start = time.time()
            # Use a unique session id to avoid conversation bleed-through
            session_id = f"eval-{idx}"
            answer_payload = engine.ask_question(question=question, session_id=session_id, user_id="evaluation_bot", use_ai=True)
            answer_time = time.time() - answer_start

            predicted_answer = answer_payload.get("answer", "")
            answer_metrics = self._compute_answer_metrics(expected_answer, predicted_answer)

            result_row = {
                "question_id": row.get("id"),
                "question": question,
                "expected_answer": expected_answer,
                "predicted_answer": predicted_answer,
                "category": row.get("category"),
                "case_title": row.get("case_title"),
                "retrieval_precision": retrieval_metrics["precision"],
                "retrieval_recall": retrieval_metrics["recall"],
                "retrieval_f1": retrieval_metrics["f1"],
                "mrr": retrieval_metrics["mrr"],
                "ndcg": retrieval_metrics["ndcg"],
                "exact_match": answer_metrics["exact_match"],
                "answer_f1": answer_metrics["f1"],
                "retrieval_time": retrieval_time,
                "answer_time": answer_time,
                "answer_type": answer_payload.get("answer_type"),
                "confidence": answer_payload.get("confidence"),
            }

            results.append(result_row)

            if verbose:
                self.stdout.write(
                    f"[{idx}/{total_questions}] {question}\n"
                    f"  Expected: {expected_answer}\n"
                    f"  Predicted: {predicted_answer}\n"
                    f"  Precision={result_row['retrieval_precision']:.2f} Recall={result_row['retrieval_recall']:.2f} "
                    f"F1={result_row['retrieval_f1']:.2f} MRR={result_row['mrr']:.2f} nDCG={result_row['ndcg']:.2f} "
                    f"Answer EM={result_row['exact_match']:.2f} Answer F1={result_row['answer_f1']:.2f}"
                )

        aggregated = self._aggregate_metrics(results)

        if output_path:
            with output_path.open("w", encoding="utf-8") as handle:
                for row in results:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            self.stdout.write(self.style.SUCCESS(f"Per-question results written to {output_path}"))

        self.stdout.write("\n=== Evaluation Summary ===")
        for key, value in aggregated.items():
            if key.endswith("_count"):
                self.stdout.write(f"{key.replace('_', ' ').title()}: {value}")
            else:
                self.stdout.write(f"{key.replace('_', ' ').title()}: {value:.4f}")

        self.stdout.write(self.style.SUCCESS("Evaluation complete."))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, maybe_relative: str) -> Path:
        path = Path(maybe_relative)
        if not path.is_absolute():
            path = Path(settings.BASE_DIR) / path
        return path

    def _load_dataset(self, dataset_path: Path, limit: int) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with dataset_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
                if limit and len(rows) >= limit:
                    break
        return rows

    def _normalize_ids(self, ids: Sequence[Any]) -> List[int]:
        normalized: List[int] = []
        for identifier in ids:
            if identifier is None:
                continue
            try:
                normalized.append(int(identifier))
            except (TypeError, ValueError):
                continue
        return normalized

    def _extract_case_ids(self, retrieval_results: Iterable[Dict[str, Any]]) -> List[int]:
        seen = set()
        unique_case_ids: List[int] = []
        for item in retrieval_results:
            metadata = item.get("metadata", {})
            case_id = metadata.get("case_id") or item.get("case_id")
            try:
                if case_id is None:
                    continue
                case_int = int(float(case_id))
            except (TypeError, ValueError):
                continue

            if case_int not in seen:
                seen.add(case_int)
                unique_case_ids.append(case_int)

        return unique_case_ids

    def _compute_retrieval_metrics(self, relevant_ids: List[int], retrieved_ids: List[int]) -> Dict[str, float]:
        relevant_set = set(relevant_ids)
        retrieved_count = len(retrieved_ids)
        relevant_count = len(relevant_set)

        tp = sum(1 for rid in retrieved_ids if rid in relevant_set)
        precision = tp / retrieved_count if retrieved_count else 0.0
        recall = tp / relevant_count if relevant_count else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        # Mean reciprocal rank (binary relevance)
        mrr = 0.0
        for index, rid in enumerate(retrieved_ids, start=1):
            if rid in relevant_set:
                mrr = 1.0 / index
                break

        # nDCG with binary relevance
        dcg = 0.0
        for index, rid in enumerate(retrieved_ids, start=1):
            rel = 1 if rid in relevant_set else 0
            if rel:
                dcg += (2 ** rel - 1) / math.log2(index + 1)

        ideal_dcg = 0.0
        for index in range(1, min(relevant_count, len(retrieved_ids)) + 1):
            ideal_dcg += (2 ** 1 - 1) / math.log2(index + 1)

        ndcg = dcg / ideal_dcg if ideal_dcg > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "mrr": mrr,
            "ndcg": ndcg,
        }

    def _compute_answer_metrics(self, gold: str, predicted: str) -> Dict[str, float]:
        gold_norm = self._normalize_text(gold)
        pred_clean = self._strip_answer_prefix(predicted)
        pred_norm = self._normalize_text(pred_clean)

        exact_match = 1.0 if gold_norm == pred_norm else 0.0

        gold_tokens = gold_norm.split()
        pred_tokens = pred_norm.split()

        common = self._counter_intersection(gold_tokens, pred_tokens)
        num_common = sum(common.values())

        if not gold_tokens or not pred_tokens:
            f1 = 1.0 if gold_tokens == pred_tokens else 0.0
        else:
            precision = num_common / len(pred_tokens) if pred_tokens else 0.0
            recall = num_common / len(gold_tokens) if gold_tokens else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        return {"exact_match": exact_match, "f1": f1}

    def _normalize_text(self, text: str) -> str:
        import re

        if text is None:
            return ""
        text = text.lower()
        text = text.strip()
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _strip_answer_prefix(self, answer: str) -> str:
        if not answer:
            return ""

        lines = answer.strip().splitlines()
        if not lines:
            return answer

        first_line = lines[0].strip()
        if first_line.lower().startswith("in ") and first_line.endswith(":"):
            remaining = "\n".join(lines[1:]).strip()
            return remaining if remaining else first_line[:-1]

        return answer

    def _counter_intersection(self, gold_tokens: Iterable[str], pred_tokens: Iterable[str]):
        from collections import Counter

        gold_counter = Counter(gold_tokens)
        pred_counter = Counter(pred_tokens)
        intersection = gold_counter & pred_counter
        return intersection

    def _aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        def mean(values: Iterable[float]) -> float:
            values = list(values)
            return statistics.mean(values) if values else 0.0

        aggregated = {
            "precision_mean": mean(row["retrieval_precision"] for row in results),
            "recall_mean": mean(row["retrieval_recall"] for row in results),
            "f1_mean": mean(row["retrieval_f1"] for row in results),
            "mrr_mean": mean(row["mrr"] for row in results),
            "ndcg_mean": mean(row["ndcg"] for row in results),
            "exact_match_mean": mean(row["exact_match"] for row in results),
            "answer_f1_mean": mean(row["answer_f1"] for row in results),
            "avg_retrieval_time": mean(row["retrieval_time"] for row in results),
            "avg_answer_time": mean(row["answer_time"] for row in results),
            "structured_lookup_count": sum(1 for row in results if row.get("answer_type") == "structured_lookup"),
            "total_evaluated_count": len(results),
        }
        return aggregated
