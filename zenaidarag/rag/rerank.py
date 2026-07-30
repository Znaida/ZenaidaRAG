"""Reranking con cross-encoder local (Fase 4, ADR-011).

Un bi-encoder (embeddings) es rapido pero aproximado; un cross-encoder evalua
la pregunta y cada fragmento JUNTOS, dando una relevancia mas precisa. Se usa
para reordenar los candidatos recuperados y quedarse con los mejores top_k.
Modelo multilingue por defecto (funciona en espanol).
"""
from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from zenaidarag.store import Retrieved


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


class CrossEncoderReranker:
    """Reordena fragmentos por relevancia usando un cross-encoder."""

    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
        self.model_name = model_name

    def rerank(
        self, question: str, candidates: Sequence[Retrieved], top_k: int
    ) -> list[Retrieved]:
        if not candidates:
            return []
        model = _load_cross_encoder(self.model_name)
        pairs = [(question, r.chunk.text) for r in candidates]
        scores = model.predict(pairs)
        ranked = sorted(
            zip(candidates, scores), key=lambda x: float(x[1]), reverse=True
        )
        return [Retrieved(chunk=r.chunk, score=float(s)) for r, s in ranked[:top_k]]
