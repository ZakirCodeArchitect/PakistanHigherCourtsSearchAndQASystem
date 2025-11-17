"""Generate a labelled evaluation dataset for chatbot testing."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from django.conf import settings
from django.core.management.base import BaseCommand

from qa_app.models import QAKnowledgeBase


class Command(BaseCommand):
    help = "Generate labelled question/answer pairs for chatbot evaluation"

    DEFAULT_OUTPUT = Path("evaluation") / "chatbot_eval_dataset.jsonl"

    SUPPORTED_FIELDS = {
        "advocates_petitioner": "Who are the petitioner's advocates in {case_title}?",
        "advocates_respondent": "Who are the respondent's advocates in {case_title}?",
        "bench": "Which bench heard {case_title}?",
        "status": "What is the case status for {case_title}?",
        "short_order": "What is the short order in {case_title}?",
        "orders": "List the court orders recorded for {case_title}.",
        "fir_number": "What is the FIR number for {case_title}?",
        "fir_date": "What is the FIR date for {case_title}?",
        "police_station": "Which police station is linked to {case_title}?",
        "under_section": "Under which sections was {case_title} filed?",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=str(self.DEFAULT_OUTPUT),
            help="Path to write the generated dataset (JSONL). Relative paths are resolved from BASE_DIR.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional limit on the number of knowledge-base entries processed (for debugging).",
        )

    def handle(self, *args, **options):
        limit = options.get("limit") or 0
        output_path = self._resolve_output_path(options.get("output"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"Collecting structured metadata entries (limit={limit or 'all'})...")

        queryset = QAKnowledgeBase.objects.filter(source_type="case_metadata").exclude(legal_entities=None)
        if limit:
            queryset = queryset[:limit]

        dataset_rows: List[Dict[str, Any]] = []

        for kb_entry in queryset.iterator():
            entity_map = self._collect_entities(kb_entry.legal_entities)
            if not entity_map:
                continue

            base_row = {
                "case_title": kb_entry.case_title,
                "case_number": kb_entry.case_number,
                "court": kb_entry.court,
                "kb_id": kb_entry.id,
                "source_case_id": kb_entry.source_case_id,
            }

            for field, question_template in self.SUPPORTED_FIELDS.items():
                if field in {"orders"}:
                    value = entity_map.get("order") or entity_map.get("orders")
                else:
                    value = entity_map.get(field)

                formatted_value = self._format_field(field, value)
                if not formatted_value:
                    continue

                row = {
                    "id": f"{kb_entry.id}_{field}",
                    "question": question_template.format(case_title=kb_entry.case_title or "this case"),
                    "expected_answer": formatted_value,
                    "category": field,
                    "relevant_case_id": kb_entry.source_case_id,
                    "relevant_kb_ids": [kb_entry.id],
                }
                row.update(base_row)
                dataset_rows.append(row)

        if not dataset_rows:
            self.stdout.write(self.style.WARNING("No structured QA rows produced."))
            return

        with output_path.open("w", encoding="utf-8") as handle:
            for row in dataset_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(dataset_rows)} rows to {output_path}"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_output_path(self, output: str) -> Path:
        path = Path(output)
        if not path.is_absolute():
            base_dir = Path(settings.BASE_DIR)
            path = base_dir / path
        return path

    def _collect_entities(self, entities: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        entity_map: Dict[str, Any] = {}
        if not entities:
            return entity_map

        for item in entities:
            if not isinstance(item, dict):
                continue
            entity_type = item.get("type")
            entity_value = item.get("value")
            if not entity_type or entity_value in (None, "", []):
                continue

            if entity_type not in entity_map:
                entity_map[entity_type] = entity_value
            else:
                existing = entity_map[entity_type]
                if isinstance(existing, list):
                    if isinstance(entity_value, list):
                        existing.extend(entity_value)
                    else:
                        existing.append(entity_value)
                else:
                    entity_map[entity_type] = [existing, entity_value]

        return entity_map

    def _format_field(self, field: str, value: Any) -> str:
        if value in (None, "", [], {}):
            return ""

        if field in {"advocates_petitioner", "advocates_respondent", "bench"}:
            values = self._to_list(value)
            return self._format_list(values)

        if field in {"status", "short_order", "fir_number", "fir_date", "police_station", "under_section"}:
            text = self._format_structured_value(value)
            return text if text else ""

        if field == "orders":
            order_lines = self._format_order_list(value)
            return " | ".join(order_lines) if order_lines else ""

        return self._format_structured_value(value)

    def _format_list(self, values: Iterable[Any]) -> str:
        clean_values = [self._format_structured_value(item) for item in values]
        clean_values = [item for item in clean_values if item]
        if not clean_values:
            return ""
        if len(clean_values) == 1:
            return clean_values[0]
        return ", ".join(clean_values[:-1]) + f" and {clean_values[-1]}"

    def _format_structured_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.lower() in {"", "n/a", "not available", "unknown", "none"}:
                return ""
            return normalized
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return ", ".join(filter(None, (self._format_structured_value(item) for item in value)))
        if isinstance(value, dict):
            parts = []
            for key, inner in value.items():
                rendered = self._format_structured_value(inner)
                if rendered:
                    parts.append(f"{key.replace('_', ' ').title()}: {rendered}")
            return "; ".join(parts)
        return str(value)

    def _format_order_list(self, orders: Any) -> List[str]:
        if orders is None:
            return []
        if not isinstance(orders, list):
            orders = [orders]

        formatted: List[str] = []
        for order in orders:
            if isinstance(order, dict):
                parts = []
                sr_number = self._format_structured_value(order.get("sr_number"))
                hearing_date = self._format_structured_value(order.get("hearing_date"))
                case_stage = self._format_structured_value(order.get("case_stage"))
                short_order = self._format_structured_value(order.get("short_order"))

                if sr_number:
                    parts.append(f"SR {sr_number}")
                if hearing_date:
                    parts.append(hearing_date)
                if case_stage:
                    parts.append(case_stage)
                if short_order:
                    parts.append(short_order)

                if parts:
                    formatted.append(" - ".join(parts))
            else:
                text = self._format_structured_value(order)
                if text:
                    formatted.append(text)

        return formatted

    def _to_list(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
