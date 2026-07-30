"""Recuperacion top-k: embebe la pregunta y consulta el VectorStore."""
from __future__ import annotations

from zenaidarag.store import Retrieved


def retrieve(question: str, store, embeddings, top_k: int = 4) -> list[Retrieved]:
    """Devuelve los top_k fragmentos mas similares a la pregunta."""
    qvec = embeddings.embed_query(question)
    return store.query(qvec, top_k)


def filter_by_score(results: list[Retrieved], min_score: float) -> list[Retrieved]:
    """Descarta fragmentos por debajo del umbral de similitud (anti-alucinacion)."""
    return [r for r in results if r.score >= min_score]
