"""Compare hybrid retrieval with hybrid + local cross-encoder reranking.

Run from the repository root with PYTHONPATH pointing to ./backend.
"""

import argparse
import json
import statistics
import time
from pathlib import Path
from uuid import UUID

from app.reranking import retrieve_with_reranking
from app.retrieval import retrieve


def metrics(ids: list[int], relevant: set[int], k: int) -> dict:
    top = ids[:k]
    positions = [i for i, chunk_id in enumerate(top, 1) if chunk_id in relevant]
    return {
        "recall_at_k": len(relevant.intersection(top)) / len(relevant),
        "precision_at_k": len(positions) / k,
        "mrr_at_k": 1 / min(positions) if positions else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("datasets/evaluation/questions.json"))
    parser.add_argument("--k", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--candidate-k", type=int, default=12)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--owner-id", required=True, type=UUID)
    args = parser.parse_args()
    if any(k < 1 or k > args.candidate_k for k in args.k) or args.candidate_k > 32:
        parser.error("Require 1 <= each k <= candidate-k <= 32")
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not cases:
        parser.error("No labeled questions provided")

    rows = {"hybrid": [], "hybrid+rerank": []}
    print("Warming up cross-encoder; initial model download may take time...", flush=True)
    from app.reranking import load_model
    load_model(args.device)
    for index, case in enumerate(cases, 1):
        relevant = set(case["relevant_chunk_ids"])
        if not relevant:
            parser.error(f"Question {index} lacks ground-truth chunk IDs")
        question = case["question"]
        t0 = time.perf_counter()
        baseline = retrieve(question, top_k=args.candidate_k, mode="hybrid", owner_id=args.owner_id)
        baseline_ms = (time.perf_counter() - t0) * 1000
        improved = retrieve_with_reranking(
            question, top_k=args.candidate_k, candidate_k=args.candidate_k, device=args.device, owner_id=args.owner_id
        )
        for name, sources, latency in (
            ("hybrid", baseline["sources"], baseline_ms),
            ("hybrid+rerank", improved["sources"], improved["total_latency_ms"]),
        ):
            chunk_ids = [item["chunk_id"] for item in sources]
            for k in args.k:
                rows[name].append({"k": k, "latency_ms": latency, **metrics(chunk_ids, relevant, k)})
        print(f"Evaluated {index}/{len(cases)}", flush=True)

    summary = {}
    for name, name_rows in rows.items():
        summary[name] = {}
        for k in args.k:
            group = [item for item in name_rows if item["k"] == k]
            summary[name][str(k)] = {
                key: round(statistics.mean(item[key] for item in group), 4)
                for key in ("recall_at_k", "precision_at_k", "mrr_at_k")
            }
            summary[name][str(k)]["median_total_latency_ms"] = round(
                statistics.median(item["latency_ms"] for item in group), 2
            )
    report = {"cases": len(cases), "candidate_k": args.candidate_k, "device": args.device,
              "model": "cross-encoder/ms-marco-MiniLM-L6-v2", "results": summary}
    output = Path("docs/results/reranking_comparison.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Saved:", output)


if __name__ == "__main__":
    main()
