import pytest

from app.reranking import reorder_candidates, retrieve_with_reranking


def test_reranking_promotes_more_relevant_chunk():
    sources = [{"chunk_id": 1}, {"chunk_id": 2}, {"chunk_id": 3}]
    ranked = reorder_candidates(sources, [0.1, 1.5, 0.4], top_k=2)
    assert [item["chunk_id"] for item in ranked] == [2, 3]
    assert ranked[0]["rerank_score"] == 1.5
    assert "rerank_score" not in sources[1]


def test_reranking_rejects_mismatched_scores():
    with pytest.raises(ValueError):
        reorder_candidates([{"chunk_id": 1}], [], top_k=1)


def test_reranking_rejects_invalid_pool():
    with pytest.raises(ValueError):
        retrieve_with_reranking("test", top_k=4, candidate_k=2)
