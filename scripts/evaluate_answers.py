
"""Evaluate ContextIQ answer faithfulness using local Ollama and Ragas."""

import argparse
import asyncio
import json
import math
import statistics
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness

API_URL = "http://127.0.0.1:8081/api/agent/ask"
OLLAMA_URL = "http://127.0.0.1:11434/v1"
MODEL = "qwen3:1.7b"


async def evaluate(limit: int) -> None:
    path = Path("datasets/evaluation/questions.json")
    cases = json.loads(path.read_text(encoding="utf-8"))

    client = AsyncOpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama",
        timeout=180.0,
        max_retries=0,
    )

    evaluator = llm_factory(
        MODEL, provider="openai", client=client
    )
    faithfulness = Faithfulness(llm=evaluator)

    results = []

    async with httpx.AsyncClient(timeout=300) as api:
        for case in cases[:limit]:
            question = case["question"]
            print(f"\nEvaluating: {question}", flush=True)

            response = await api.post(
                API_URL,
                json={
                    "question": question,
                    "top_k": 4,
                    "mode": "hybrid",
                },
            )
            response.raise_for_status()
            data = response.json()

            record = {
                "question": question,
                "answer": data["answer"],
                "abstained": data["abstained"],
                "source_ids": [
                    source["chunk_id"]
                    for source in data["sources"]
                ],
                "faithfulness": None,
                "evaluation_error": None,
            }

            if not data["abstained"] and data["sources"]:
                try:
                    score = await faithfulness.ascore(
                        user_input=question,
                        response=data["answer"],
                        retrieved_contexts=[
                            source["excerpt"]
                            for source in data["sources"]
                        ],
                    )
                    value = float(score.value)
                    if math.isfinite(value):
                        record["faithfulness"] = value
                except Exception as exc:
                    record["evaluation_error"] = (
                        f"{type(exc).__name__}: {exc}"
                    )

            results.append(record)
            print(
                "Faithfulness:",
                record["faithfulness"],
                flush=True,
            )

    scores = [
        item["faithfulness"]
        for item in results
        if item["faithfulness"] is not None
    ]

    report = {
        "model": MODEL,
        "cases": len(results),
        "scored_cases": len(scores),
        "mean_faithfulness": (
            statistics.mean(scores) if scores else None
        ),
        "results": results,
    }

    output = Path("docs/results/answer_evaluation.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nReport saved to:", output)
    print(json.dumps({
        "cases": report["cases"],
        "scored_cases": report["scored_cases"],
        "mean_faithfulness": report["mean_faithfulness"],
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    if not 1 <= args.limit <= 15:
        parser.error("--limit must be between 1 and 15")

    asyncio.run(evaluate(args.limit))
