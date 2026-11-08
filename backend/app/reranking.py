"""Optional local PyTorch cross-encoder reranking for ContextIQ.

The model is loaded lazily and is not needed by the existing FastAPI routes.
"""

from functools import lru_cache
from time import perf_counter

from app.retrieval import retrieve

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"


@lru_cache(maxsize=2)
def load_model(device: str = "cpu"):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(MODEL_NAME, device=device, max_length=512)


def reorder_candidates(sources: list[dict], scores: list[float], top_k: int) -> list[dict]:
    """Stable rank by cross-encoder score; preserve original source metadata."""
    if len(sources) != len(scores):
        raise ValueError("Each candidate must have exactly one score")
    if top_k < 1:
        raise ValueError("top_k must be positive")
    ranked = [dict(source, rerank_score=float(score)) for source, score in zip(sources, scores)]
    ranked.sort(key=lambda source: source["rerank_score"], reverse=True)
    return ranked[:top_k]


def rerank(question: str, candidates: list[dict], top_k: int, device: str = "cpu") -> list[dict]:
    """Model inference using question-passage pairs; scores are not calibrated probabilities."""
    if not candidates:
        return []
    model = load_model(device)
    pairs = [(question, source["excerpt"]) for source in candidates]
    scores = model.predict(pairs, batch_size=8, show_progress_bar=False)
    return reorder_candidates(candidates, [float(score) for score in scores], top_k)


def retrieve_with_reranking(
    question: str,
    top_k: int = 4,
    candidate_k: int = 12,
    device: str = "cpu",
) -> dict:
    """Retrieve a larger hybrid pool then cross-encoder rerank it."""
    if not 1 <= top_k <= candidate_k <= 32:
        raise ValueError("Require 1 <= top_k <= candidate_k <= 32")
    started = perf_counter()
    first_stage = retrieve(question, top_k=candidate_k, mode="hybrid")
    sources = rerank(question, first_stage["sources"], top_k, device=device)
    return {
        "sources": sources,
        "mode": "hybrid+rerank",
        "candidate_k": candidate_k,
        "retrieval_latency_ms": first_stage["latency_ms"],
        "total_latency_ms": round((perf_counter() - started) * 1000, 2),
    }
