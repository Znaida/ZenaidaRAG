"""Busqueda hibrida: BM25 (keyword) + fusion RRF con la semantica (Fase 4).

La recuperacion semantica (embeddings) capta significado; BM25 capta coincidencia
exacta de terminos (nombres, dosis, siglas). Se fusionan con Reciprocal Rank
Fusion (RRF), robusto porque combina *rankings*, no scores de distinta escala.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from zenaidarag.store import Chunk, Retrieved

_TOKEN = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def bm25_rank(question: str, chunks: Sequence[Chunk], top_n: int) -> list[Retrieved]:
    """Ordena `chunks` por relevancia BM25 respecto a la pregunta."""
    from rank_bm25 import BM25Okapi

    if not chunks:
        return []
    corpus = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(question))
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [Retrieved(chunk=c, score=float(s)) for c, s in ranked[:top_n]]


def rrf_fuse(
    rankings: Sequence[Sequence[Retrieved]], k: int = 60, top_n: int | None = None
) -> list[Retrieved]:
    """Fusiona varias listas rankeadas con Reciprocal Rank Fusion.

    score(doc) = sum_r 1 / (k + rank_r(doc)). El `score` resultante se guarda en
    Retrieved.score (util para debug); el orden es lo que importa.
    """
    fused: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, r in enumerate(ranking, start=1):
            cid = r.chunk.id
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
            by_id[cid] = r.chunk
    ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)
    out = [Retrieved(chunk=by_id[cid], score=score) for cid, score in ordered]
    return out[:top_n] if top_n is not None else out
