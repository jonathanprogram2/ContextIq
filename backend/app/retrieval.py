"""Hybrid pgvector + PostgreSQL full-text retrieval with reciprocal rank fusion."""

import time

import psycopg
from psycopg.rows import dict_row

from app.documents import database_url
from app.rag import EMBED_MODEL, embed_texts, vector_literal


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    """Fuse multiple ordered candidate ID lists; scores are rankings, not probabilities."""
    scores: dict[int, float] = {}
    for ids in rankings:
        for rank, item_id in enumerate(dict.fromkeys(ids), 1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


def retrieve(question: str, top_k: int = 4, mode: str = "hybrid") -> dict:
    """Return grounded candidate metadata; mode is 'vector' or 'hybrid'."""
    if mode not in {"vector", "hybrid"}:
        raise ValueError("mode must be vector or hybrid")
    started = time.perf_counter()
    vector = vector_literal(embed_texts([question])[0])
    pool = max(top_k * 4, 12)
    with psycopg.connect(database_url(), row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.document_id::text AS document_id, d.filename,
                   c.page_number, c.text_content, 
                   1 - (c.embedding <=> %s::vector) AS similarity
            FROM document_chunks c JOIN documents d ON d.id = c.document_id
            WHERE c.embedding_model = %s
            ORDER BY c.embedding <=> %s::vector LIMIT %s
            """,
            (vector, EMBED_MODEL, vector, pool),
        )
        vector_hits = cur.fetchall()
        lexical_hits = []
        if mode == "hybrid":
            cur.execute(
                """
                SELECT c.id, c.document_id::text AS document_id, d.filename,
                       c.page_number, c.text_content,
                       ts_rank_cd(to_tsvector('english', c.text_content),
                                  websearch_to_tsquery('english', %s)) AS lexical_rank
                FROM document_chunks c JOIN documents d ON d.id = c.document_id
                WHERE c.embedding_model = %s
                  AND to_tsvector('english', c.text_content)
                      @@ websearch_to_tsquery('english', %s)
                ORDER BY lexical_rank DESC, c.id ASC LIMIT %s
                """,
                (question, EMBED_MODEL, question, pool),
            )
            lexical_hits = cur.fetchall()
    by_id = {row["id"]: row for row in lexical_hits}
    by_id.update({row["id"]: row for row in vector_hits})
    scores = reciprocal_rank_fusion(
        [[row["id"] for row in vector_hits], [row["id"] for row in lexical_hits]]
        if mode == "hybrid" else [[row["id"] for row in vector_hits]]
    )
    similarity_by_id = {row["id"]: float(row["similarity"]) for row in vector_hits}
    ordered = sorted(scores, key=lambda item_id: (-scores[item_id], item_id))[:top_k]
    hits = [
        {
            "chunk_id": item_id,
            "document_id": by_id[item_id]["document_id"],
            "filename": by_id[item_id]["filename"],
            "page_number": by_id[item_id]["page_number"],
            "excerpt": by_id[item_id]["text_content"],
            "similarity": round(similarity_by_id[item_id], 4)
            if item_id in similarity_by_id else None,
            "fusion_score": round(scores[item_id], 6),
        }
        for item_id in ordered
    ]
    return {"sources": hits, "mode": mode, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
