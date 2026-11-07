"""Repeated K=1,2,4 vector-vs-hybrid benchmark on verified labeled chunks."""

import argparse
import json
import random
import statistics
from pathlib import Path

from app.retrieval import retrieve
from evaluate_retrieval import score_case


def run_suite(cases: list[dict], ks: list[int], repeats: int, seed: int) -> dict:
    rng = random.Random(seed)
    report: dict = {"questions": len(cases), "repeats": repeats, "results": {}}
    for k in ks:
        records = {"vector": [], "hybrid": []}
        for _ in range(repeats):
            jobs = [(case, mode) for case in cases for mode in ("vector", "hybrid")]
            rng.shuffle(jobs)
            for case, mode in jobs:
                relevant = set(case["relevant_chunk_ids"])
                if not relevant:
                    raise ValueError("Every benchmark case must have verified relevant IDs")
                response = retrieve(case["question"], top_k=k, mode=mode)
                scores = score_case(
                    [source["chunk_id"] for source in response["sources"]], relevant, k
                )
                scores["latency_ms"] = response["latency_ms"]
                records[mode].append(scores)
        report["results"][str(k)] = {
            mode: {
                "recall_at_k": round(statistics.mean(r["recall_at_k"] for r in rows), 4),
                "precision_at_k": round(statistics.mean(r["precision_at_k"] for r in rows), 4),
                "mrr_at_k": round(statistics.mean(r["reciprocal_rank"] for r in rows), 4),
                "latency_median_ms": round(statistics.median(r["latency_ms"] for r in rows), 2),
            }
            for mode, rows in records.items()
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("datasets/evaluation/questions.json"))
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--k", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("docs/results/retrieval_comparison.json"))
    args = parser.parse_args()
    if args.repeats < 1 or args.repeats > 10 or any(k < 1 or k > 8 for k in args.k):
        parser.error("Use --repeats from 1 to 10 and K values from 1 to 8")
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not cases:
        parser.error("No benchmark cases; run scripts/prepare_evaluation.py first")
    report = run_suite(cases, sorted(set(args.k)), args.repeats, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
