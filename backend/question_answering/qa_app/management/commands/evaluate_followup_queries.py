"""Evaluate chatbot on follow-up queries with session context."""

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand

from services.enhanced_qa_engine import EnhancedQAEngine
from qa_app.services.qa_retrieval_service import QARetrievalService


class Command(BaseCommand):
    help = "Evaluate chatbot on follow-up queries maintaining session context"

    DEFAULT_DATASET = Path("evaluation") / "chatbot_eval_dataset.jsonl"

    # Follow-up question templates
    FOLLOWUP_TEMPLATES = [
        "what is the court order",
        "who are the advocates",
        "what is the FIR number",
        "what is the case status",
        "give me details for this case",
        "what is the bench",
        "what is the short order",
        "give me a summary",
        "what sections were filed",
        "what is the hearing date",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            type=str,
            default=str(self.DEFAULT_DATASET),
            help="Path to the JSONL dataset",
        )
        parser.add_argument(
            "--num-cases",
            type=int,
            default=25,
            help="Number of unique cases to evaluate (default: 25)",
        )
        parser.add_argument(
            "--followups-per-case",
            type=int,
            default=8,
            help="Number of follow-up queries per case (default: 8)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="evaluation/followup_evaluation_results.xlsx",
            help="Output Excel file path",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=10,
            help="Top K results for retrieval metrics",
        )

    def handle(self, *args, **options):
        dataset_path = self._resolve_path(options.get("dataset"))
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found at {dataset_path}")

        num_cases = options.get("num_cases", 25)
        followups_per_case = options.get("followups_per_case", 8)
        output_path = self._resolve_path(options.get("output"))
        top_k = options.get("top_k", 10)

        self.stdout.write(f"Loading dataset from {dataset_path}...")
        all_queries = self._load_dataset(dataset_path, limit=0)
        
        # Group queries by case_id to get unique cases
        cases_dict = {}
        for query in all_queries:
            case_id = query.get("relevant_case_id")
            if case_id:
                if case_id not in cases_dict:
                    cases_dict[case_id] = {
                        "case_id": case_id,
                        "case_title": query.get("case_title"),
                        "case_number": query.get("case_number"),
                        "initial_query": query.get("question"),
                        "expected_answer": query.get("expected_answer"),
                    }
        
        # Select unique cases
        unique_cases = list(cases_dict.values())[:num_cases]
        self.stdout.write(f"Selected {len(unique_cases)} unique cases for evaluation")
        self.stdout.write("Initializing chatbot components...")

        start_time = time.time()
        engine = EnhancedQAEngine()
        retrieval_service: QARetrievalService = engine.qa_retrieval_service
        init_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Components initialized in {init_time:.2f}s"))

        all_results = []

        for case_idx, case_info in enumerate(unique_cases, 1):
            case_id = case_info["case_id"]
            case_title = case_info["case_title"]
            case_number = case_info["case_number"]
            initial_query = case_info["initial_query"]
            
            self.stdout.write(f"\n[{case_idx}/{len(unique_cases)}] Evaluating case: {case_number}")
            
            # Create a unique session for this case
            session_id = f"followup-eval-{case_id}-{case_idx}"
            
            # Generate follow-up questions
            followup_queries = self._generate_followup_queries(
                case_title, case_number, followups_per_case
            )
            
            # Run initial query
            self.stdout.write(f"  Initial query: {initial_query}")
            initial_result = self._evaluate_query(
                engine, retrieval_service, initial_query, 
                case_info.get("expected_answer", ""), 
                case_id, session_id, top_k, turn_number=0
            )
            initial_result["case_id"] = case_id
            initial_result["case_number"] = case_number
            initial_result["case_title"] = case_title
            initial_result["query_type"] = "initial"
            all_results.append(initial_result)
            
            # Run follow-up queries
            for followup_idx, followup_query in enumerate(followup_queries, 1):
                self.stdout.write(f"  Follow-up {followup_idx}: {followup_query}")
                followup_result = self._evaluate_query(
                    engine, retrieval_service, followup_query,
                    "",  # No expected answer for follow-ups
                    case_id, session_id, top_k, turn_number=followup_idx
                )
                followup_result["case_id"] = case_id
                followup_result["case_number"] = case_number
                followup_result["case_title"] = case_title
                followup_result["query_type"] = "followup"
                all_results.append(followup_result)

        # Export to Excel
        self.stdout.write(f"\nExporting results to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._export_to_excel(all_results, output_path)
        
        # Print summary
        self._print_summary(all_results)
        
        self.stdout.write(self.style.SUCCESS(f"\nEvaluation complete. Results saved to {output_path}"))

    def _generate_followup_queries(self, case_title: str, case_number: str, count: int) -> List[str]:
        """Generate follow-up questions for a case."""
        queries = []
        templates = self.FOLLOWUP_TEMPLATES.copy()
        
        # Shuffle and select templates
        import random
        random.seed(42)  # For reproducibility
        selected = random.sample(templates, min(count, len(templates)))
        
        for template in selected:
            # Use "this case" for contextual follow-ups
            if "this case" not in template and "case" not in template.lower():
                queries.append(f"{template} for this case")
            else:
                queries.append(template)
        
        return queries

    def _evaluate_query(
        self, 
        engine: EnhancedQAEngine,
        retrieval_service: QARetrievalService,
        question: str,
        expected_answer: str,
        relevant_case_id: int,
        session_id: str,
        top_k: int,
        turn_number: int
    ) -> Dict[str, Any]:
        """Evaluate a single query and return metrics."""
        
        # Retrieval evaluation
        retrieval_start = time.time()
        retrieval_results = retrieval_service.retrieve_for_qa(question, top_k=top_k)
        retrieval_time = time.time() - retrieval_start
        
        retrieved_case_ids = self._extract_case_ids(retrieval_results)
        relevant_case_ids = [relevant_case_id] if relevant_case_id else []
        retrieval_metrics = self._compute_retrieval_metrics(relevant_case_ids, retrieved_case_ids)
        
        # Answer generation
        answer_start = time.time()
        answer_payload = engine.ask_question(
            question=question, 
            session_id=session_id, 
            user_id="evaluation_bot", 
            use_ai=True
        )
        answer_time = time.time() - answer_start
        
        predicted_answer = answer_payload.get("answer", "")
        
        # Compute answer metrics if expected answer is provided
        if expected_answer:
            answer_metrics = self._compute_answer_metrics(expected_answer, predicted_answer)
        else:
            answer_metrics = {"exact_match": 0.0, "f1": 0.0}
        
        return {
            "turn_number": turn_number,
            "question": question,
            "expected_answer": expected_answer,
            "predicted_answer": predicted_answer,
            "retrieval_precision": retrieval_metrics["precision"],
            "retrieval_recall": retrieval_metrics["recall"],
            "retrieval_f1": retrieval_metrics["f1"],
            "mrr": retrieval_metrics["mrr"],
            "ndcg": retrieval_metrics["ndcg"],
            "exact_match": answer_metrics["exact_match"],
            "answer_f1": answer_metrics["f1"],
            "retrieval_time": retrieval_time,
            "answer_time": answer_time,
            "total_time": retrieval_time + answer_time,
            "answer_type": answer_payload.get("answer_type"),
            "confidence": answer_payload.get("confidence"),
            "session_id": session_id,
        }

    def _export_to_excel(self, results: List[Dict[str, Any]], output_path: Path):
        """Export results to Excel file."""
        df = pd.DataFrame(results)
        
        # Reorder columns for better readability
        column_order = [
            "case_id", "case_number", "case_title", "turn_number", "query_type",
            "question", "expected_answer", "predicted_answer",
            "retrieval_precision", "retrieval_recall", "retrieval_f1", "mrr", "ndcg",
            "exact_match", "answer_f1",
            "retrieval_time", "answer_time", "total_time",
            "answer_type", "confidence", "session_id"
        ]
        
        # Only include columns that exist
        available_columns = [col for col in column_order if col in df.columns]
        df = df[available_columns]
        
        # Write to Excel with formatting
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Results', index=False)
            
            # Create summary sheet
            summary_data = {
                "Metric": [
                    "Total Queries",
                    "Initial Queries",
                    "Follow-up Queries",
                    "Avg Retrieval Precision",
                    "Avg Retrieval Recall",
                    "Avg Retrieval F1",
                    "Avg MRR",
                    "Avg nDCG",
                    "Avg Answer F1",
                    "Avg Exact Match",
                    "Avg Retrieval Time (s)",
                    "Avg Answer Time (s)",
                    "Avg Total Time (s)",
                ],
                "Value": [
                    len(results),
                    len([r for r in results if r.get("query_type") == "initial"]),
                    len([r for r in results if r.get("query_type") == "followup"]),
                    statistics.mean([r.get("retrieval_precision", 0) for r in results]),
                    statistics.mean([r.get("retrieval_recall", 0) for r in results]),
                    statistics.mean([r.get("retrieval_f1", 0) for r in results]),
                    statistics.mean([r.get("mrr", 0) for r in results]),
                    statistics.mean([r.get("ndcg", 0) for r in results]),
                    statistics.mean([r.get("answer_f1", 0) for r in results]),
                    statistics.mean([r.get("exact_match", 0) for r in results]),
                    statistics.mean([r.get("retrieval_time", 0) for r in results]),
                    statistics.mean([r.get("answer_time", 0) for r in results]),
                    statistics.mean([r.get("total_time", 0) for r in results]),
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Create per-case summary
            case_summary = []
            for case_id in set(r.get("case_id") for r in results if r.get("case_id")):
                case_results = [r for r in results if r.get("case_id") == case_id]
                case_summary.append({
                    "case_id": case_id,
                    "case_number": case_results[0].get("case_number") if case_results else "",
                    "case_title": case_results[0].get("case_title") if case_results else "",
                    "total_queries": len(case_results),
                    "avg_precision": statistics.mean([r.get("retrieval_precision", 0) for r in case_results]),
                    "avg_recall": statistics.mean([r.get("retrieval_recall", 0) for r in case_results]),
                    "avg_f1": statistics.mean([r.get("retrieval_f1", 0) for r in case_results]),
                    "avg_mrr": statistics.mean([r.get("mrr", 0) for r in case_results]),
                    "avg_ndcg": statistics.mean([r.get("ndcg", 0) for r in case_results]),
                    "avg_answer_f1": statistics.mean([r.get("answer_f1", 0) for r in case_results]),
                })
            case_summary_df = pd.DataFrame(case_summary)
            case_summary_df.to_excel(writer, sheet_name='Per-Case Summary', index=False)

    def _print_summary(self, results: List[Dict[str, Any]]):
        """Print evaluation summary to console."""
        initial_results = [r for r in results if r.get("query_type") == "initial"]
        followup_results = [r for r in results if r.get("query_type") == "followup"]
        
        self.stdout.write("\n=== Evaluation Summary ===")
        self.stdout.write(f"Total Queries: {len(results)}")
        self.stdout.write(f"  Initial: {len(initial_results)}")
        self.stdout.write(f"  Follow-up: {len(followup_results)}")
        
        self.stdout.write("\n=== Retrieval Metrics (All Queries) ===")
        self.stdout.write(f"Precision: {statistics.mean([r.get('retrieval_precision', 0) for r in results]):.4f}")
        self.stdout.write(f"Recall: {statistics.mean([r.get('retrieval_recall', 0) for r in results]):.4f}")
        self.stdout.write(f"F1: {statistics.mean([r.get('retrieval_f1', 0) for r in results]):.4f}")
        self.stdout.write(f"MRR: {statistics.mean([r.get('mrr', 0) for r in results]):.4f}")
        self.stdout.write(f"nDCG: {statistics.mean([r.get('ndcg', 0) for r in results]):.4f}")
        
        self.stdout.write("\n=== Answer Metrics (Initial Queries Only) ===")
        if initial_results:
            self.stdout.write(f"Answer F1: {statistics.mean([r.get('answer_f1', 0) for r in initial_results]):.4f}")
            self.stdout.write(f"Exact Match: {statistics.mean([r.get('exact_match', 0) for r in initial_results]):.4f}")
        
        self.stdout.write("\n=== Performance ===")
        self.stdout.write(f"Avg Retrieval Time: {statistics.mean([r.get('retrieval_time', 0) for r in results]):.4f}s")
        self.stdout.write(f"Avg Answer Time: {statistics.mean([r.get('answer_time', 0) for r in results]):.4f}s")
        self.stdout.write(f"Avg Total Time: {statistics.mean([r.get('total_time', 0) for r in results]):.4f}s")

    # Helper methods (same as evaluate_chatbot.py)
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

        # Token-level F1
        gold_tokens = set(gold_norm.split())
        pred_tokens = set(pred_norm.split())

        if not gold_tokens:
            f1 = 1.0 if not pred_tokens else 0.0
        else:
            intersection = gold_tokens & pred_tokens
            if not intersection:
                f1 = 0.0
            else:
                precision = len(intersection) / len(pred_tokens) if pred_tokens else 0.0
                recall = len(intersection) / len(gold_tokens)
                f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        return {"exact_match": exact_match, "f1": f1}

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        text = text.lower().strip()
        # Remove extra whitespace
        text = " ".join(text.split())
        # Remove common punctuation for comparison
        import re
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def _strip_answer_prefix(self, answer: str) -> str:
        """Strip common answer prefixes like 'Sure —'."""
        if not answer:
            return ""
        prefixes = ["sure —", "sure -", "sure:", "sure,"]
        answer_lower = answer.lower().strip()
        for prefix in prefixes:
            if answer_lower.startswith(prefix):
                return answer[len(prefix):].strip()
        return answer.strip()

