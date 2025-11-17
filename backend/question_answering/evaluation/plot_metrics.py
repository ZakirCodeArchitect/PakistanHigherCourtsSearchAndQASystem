"""Generate a bar chart of chatbot evaluation metrics."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def main(dataset_path: Path, output_path: Path) -> None:
    sns.set_theme(style="whitegrid")

    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if not rows:
        raise SystemExit(f"No data found in {dataset_path}")

    df = pd.DataFrame(rows)

    metric_values = {
        "Precision": df["retrieval_precision"].mean(),
        "Recall": df["retrieval_recall"].mean(),
        "F1": df["retrieval_f1"].mean(),
        "MRR": df["mrr"].mean(),
        "nDCG": df["ndcg"].mean(),
        "Answer F1": df["answer_f1"].mean(),
    }

    metric_df = (
        pd.Series(metric_values)
        .sort_index()
        .rename_axis("Metric")
        .to_frame("Score")
        .reset_index()
    )

    plt.figure(figsize=(8, 5))
    bar = sns.barplot(data=metric_df, x="Metric", y="Score", palette="viridis")

    for idx, row in metric_df.iterrows():
        bar.text(idx, row["Score"] + 0.01, f"{row['Score']:.2f}", ha="center", va="bottom", fontsize=10)

    plt.ylim(0, 1.1)
    plt.title("Chatbot Evaluation Metrics (Subset, n=300)")
    plt.ylabel("Score")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"Bar chart saved to {output_path}")


if __name__ == "__main__":
    eval_dir = Path(__file__).resolve().parent
    dataset = eval_dir / "chatbot_eval_subset.jsonl"
    output = eval_dir / "chatbot_eval_metrics.png"
    main(dataset, output)
