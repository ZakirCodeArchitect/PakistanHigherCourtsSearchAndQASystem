import json
import random
from pathlib import Path
from typing import List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

try:
    from sentence_transformers import CrossEncoder, InputExample
    from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator
except ImportError as exc:  # pragma: no cover - optional dependency
    CrossEncoder = None  # type: ignore
    InputExample = None  # type: ignore
    CEBinaryClassificationEvaluator = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from torch.utils.data import DataLoader


class Command(BaseCommand):
    """
    Fine-tune a CrossEncoder reranker on exported benchmark training data.

    Usage example:
        python manage.py train_learned_reranker \\
            --dataset ..\\..\\reports\\reranker_training.jsonl \\
            --base-model cross-encoder/ms-marco-MiniLM-L-6-v2 \\
            --output-name hc_reranker_v1
    """

    help = "Train a learned reranker (cross-encoder) using exported benchmark data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset",
            required=True,
            help="Path to JSONL dataset produced by export_benchmark_training_data.",
        )
        parser.add_argument(
            "--output-name",
            required=True,
            help="Name for the saved model directory under LEARNED_RERANKER_DIR.",
        )
        parser.add_argument(
            "--base-model",
            default="cross-encoder/ms-marco-MiniLM-L-6-v2",
            help="HuggingFace model name or path to use as the base cross-encoder.",
        )
        parser.add_argument(
            "--max-length",
            type=int,
            default=512,
            help="Maximum sequence length for the cross-encoder.",
        )
        parser.add_argument(
            "--epochs",
            type=int,
            default=2,
            help="Number of fine-tuning epochs (default: 2).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=16,
            help="Training batch size (default: 16).",
        )
        parser.add_argument(
            "--lr",
            type=float,
            default=2e-5,
            help="Learning rate (default: 2e-5).",
        )
        parser.add_argument(
            "--validation-split",
            type=float,
            default=0.1,
            help="Fraction of data reserved for validation (default: 0.1).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for shuffling (default: 42).",
        )

    def handle(self, *args, **options):
        if CrossEncoder is None or InputExample is None:
            raise CommandError(
                "sentence-transformers is required for this command. "
                "Install it with `pip install sentence-transformers`."
            ) from _IMPORT_ERROR

        dataset_path = Path(options["dataset"]).expanduser()
        if not dataset_path.exists():
            raise CommandError(f"Dataset not found at {dataset_path}")

        output_name = options["output_name"].strip()
        if not output_name:
            raise CommandError("--output-name cannot be empty.")

        base_model = options["base_model"]
        max_length = options["max_length"]
        epochs = options["epochs"]
        batch_size = options["batch_size"]
        learning_rate = options["lr"]
        validation_split = options["validation_split"]
        seed = options["seed"]

        if not (0.0 <= validation_split < 1.0):
            raise CommandError("--validation-split must be between 0 (inclusive) and 1 (exclusive).")

        random.seed(seed)

        records = self._load_records(dataset_path)
        if not records:
            raise CommandError("Dataset did not contain any valid records.")

        random.shuffle(records)
        split_index = int(len(records) * (1 - validation_split))
        if split_index <= 0:
            raise CommandError("Validation split is too large; no samples left for training.")

        train_examples = records[:split_index]
        val_examples = records[split_index:] if validation_split > 0 else []

        self.stdout.write(f"Loaded {len(records)} samples ({len(train_examples)} train / {len(val_examples)} val)")

        model = CrossEncoder(
            base_model,
            num_labels=1,
            max_length=max_length,
        )

        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
        evaluator = (
            CEBinaryClassificationEvaluator.from_input_examples(val_examples, name="val")
            if val_examples
            else None
        )

        warmup_steps = int(len(train_dataloader) * epochs * 0.1)
        evaluation_steps = max(100, len(train_dataloader)) if evaluator else 0

        self.stdout.write(
            self.style.NOTICE(
                f"Training cross-encoder from {base_model} for {epochs} epochs "
                f"(batch_size={batch_size}, lr={learning_rate}, warmup_steps={warmup_steps})"
            )
        )

        model.fit(
            train_dataloader=train_dataloader,
            evaluator=evaluator,
            epochs=epochs,
            evaluation_steps=evaluation_steps if evaluator else 0,
            warmup_steps=warmup_steps,
            optimizer_params={"lr": learning_rate},
            show_progress_bar=True,
        )

        output_dir = settings.LEARNED_RERANKER_DIR / output_name
        output_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"Saving fine-tuned model to {output_dir}")
        model.save(output_dir)

        metadata = {
            "base_model": base_model,
            "max_length": max_length,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "validation_split": validation_split,
            "seed": seed,
            "train_samples": len(train_examples),
            "val_samples": len(val_examples),
            "dataset_path": str(dataset_path),
        }
        metadata_path = output_dir / "training_metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Training complete. Update LEARNED_RERANKER_MODEL in .env to enable the model."))

    def _load_records(self, dataset_path: Path) -> List[InputExample]:
        records: List[InputExample] = []
        with dataset_path.open("r", encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    self.stderr.write(f"Skipping malformed JSON on line {line_number}")
                    continue

                query_text = record.get("query_text")
                case_text = self._compose_case_text(record)
                label = record.get("label")

                if not query_text or not case_text or label is None:
                    continue

                try:
                    label_value = float(label)
                except (TypeError, ValueError):
                    continue

                records.append(
                    InputExample(
                        texts=[
                            f"Query: {query_text}",
                            f"Candidate: {case_text}",
                        ],
                        label=label_value,
                    )
                )
        return records

    def _compose_case_text(self, record: dict) -> str:
        parts: List[str] = []
        for key in ("case_title", "case_number", "case_court", "case_status", "case_bench"):
            value = record.get(key)
            if value:
                parts.append(f"{key.replace('case_', '').replace('_', ' ').title()}: {value}")

        summary = record.get("case_summary")
        if summary:
            parts.append(f"Summary: {summary}")

        abstract = record.get("case_abstract")
        if abstract:
            parts.append(f"Abstract: {abstract}")

        subjects = record.get("case_subject_tags") or []
        if subjects:
            parts.append("Subjects: " + ", ".join(subjects))

        sections = record.get("case_section_tags") or []
        if sections:
            parts.append("Sections: " + ", ".join(sections))

        metadata = record.get("case_metadata") or {}
        if metadata and metadata.get("abstract_sentences"):
            parts.append("Abstract sentences: " + " ".join(metadata["abstract_sentences"]))

        return " | ".join(parts)

