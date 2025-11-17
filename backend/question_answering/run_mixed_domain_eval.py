import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django

django.setup()

from question_answering.services.enhanced_qa_engine import EnhancedQAEngine


def load_queries(dataset_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if len(data) != 50:
        raise ValueError(f"Expected 50 queries, found {len(data)} in {dataset_path}")
    return data


def run_eval(
    engine: EnhancedQAEngine,
    queries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(queries, start=1):
        question = item["question"]
        category = item.get("category", "unknown")

        response = engine.ask_question(
            question=question,
            session_id=None,
            user_id="mixed_domain_eval",
        )

        sources = response.get("sources") or []
        source_titles = []
        source_case_numbers = []
        for src in sources:
            if isinstance(src, dict):
                title = src.get("title") or src.get("case_title")
                number = src.get("case_number")
            else:
                title = str(src)
                number = ""
            if title:
                source_titles.append(str(title))
            if number:
                source_case_numbers.append(str(number))

        results.append(
            {
                "index": idx,
                "category": category,
                "question": question,
                "answer": response.get("answer", ""),
                "answer_type": response.get("answer_type"),
                "confidence": response.get("confidence"),
                "session_id": response.get("session_id"),
                "sources": sources,
                "source_titles": "; ".join(source_titles),
                "source_case_numbers": "; ".join(source_case_numbers),
                "retrieval_method": response.get("search_method"),
                "documents_found": response.get("documents_found"),
            }
        )

    return results


def save_outputs(results: List[Dict[str, Any]], json_path: Path, excel_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    df = pd.DataFrame(results)
    df.to_excel(excel_path, index=False)


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    summary["total_queries"] = len(results)
    answer_types = {}
    for row in results:
        at = row.get("answer_type") or "unknown"
        answer_types[at] = answer_types.get(at, 0) + 1
    summary["answer_type_counts"] = answer_types
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run mixed-domain evaluation queries.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=BASE_DIR / "evaluation" / "mixed_domain_queries.json",
        help="Path to the JSON dataset containing 50 queries.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        help="Where to store the JSON results.",
    )
    parser.add_argument(
        "--output-excel",
        type=Path,
        required=True,
        help="Where to store the Excel results.",
    )
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Disable structured lookup so every query uses the RAG pipeline.",
    )
    args = parser.parse_args()

    queries = load_queries(args.dataset)
    engine = EnhancedQAEngine()

    if args.rag_only:
        def _skip_structured(*_args, **_kwargs):
            return None

        engine._attempt_structured_answer = _skip_structured  # type: ignore[attr-defined]
        print("Structured lookup disabled: forcing RAG path for every query.")

    results = run_eval(engine, queries)
    save_outputs(results, args.output_json, args.output_excel)
    summary = summarize(results)

    print("=== Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"Wrote JSON to {args.output_json}")
    print(f"Wrote Excel to {args.output_excel}")


if __name__ == "__main__":
    main()

