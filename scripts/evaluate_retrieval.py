"""Run labeled retrieval benchmarks. Execute from backend with PYTHONPATH=."""

import argparse
import json
import statistics
from pathlib import Path

from app.retrieval import retrieve


def score_case(predicted: list[int], relevant: set[int], k: int) -> dict[str, float]:
    top = predicted[:k]
    hits = len(relevant.intersection(top))
    first = next((position for position, cid in enumerate(top, 1) if cid in relevant), None)
    return {"recall_at_k": hits / len(relevant) if relevant else 0.0,
            "precision_at_k": hits / k,
            "reciprocal_rank": 1 / first if first else 0.0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.k <= 8:
        parser.error("--k must be between 1 and 8")
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        parser.error("Dataset needs labeled cases; none supplied. Do not invent evaluation results.")
    report = {}
    for mode in ("vector", "hybrid"):
        results = []
        for case in cases:
            relevant = set(case["relevant_chunk_ids"])
            if not relevant:
                parser.error("Each case must have at least one verified relevant chunk ID")
            response = retrieve(case["question"], top_k=args.k, mode=mode)
            row = score_case([source["chunk_id"] for source in response["sources"]], relevant, args.k)
            row["latency_ms"] = response["latency_ms"]
            results.append(row)
        report[mode] = {name: round(statistics.mean(row[name] for row in results), 4)
                        for name in ("recall_at_k", "precision_at_k", "reciprocal_rank", "latency_ms")}
    print(json.dumps({"cases": len(cases), "k": args.k, "metrics": report}, indent=2))


if __name__ == "__main__":
    main()
