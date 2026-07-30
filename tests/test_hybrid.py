"""Tests de busqueda hibrida: BM25 + fusion RRF (Fase 4)."""
from __future__ import annotations

from zenaidarag.rag.hybrid import bm25_rank, rrf_fuse
from zenaidarag.store import Chunk, Retrieved


def _c(cid, text, source="s.md"):
    return Chunk(id=cid, text=text, source=source)


def test_bm25_ranks_exact_term_first():
    chunks = [
        _c("1", "el gato duerme mucho durante el dia"),
        _c("2", "la vacuna antirrabica es obligatoria en muchos paises"),
        _c("3", "el perro necesita ejercicio diario"),
    ]
    ranked = bm25_rank("vacuna antirrabica obligatoria", chunks, top_n=3)
    assert ranked[0].chunk.id == "2"


def test_bm25_empty():
    assert bm25_rank("algo", [], top_n=5) == []


def test_rrf_fuse_combines_rankings():
    a = _c("A", "a")
    b = _c("B", "b")
    c = _c("C", "c")
    r1 = [Retrieved(a, 0.9), Retrieved(b, 0.8), Retrieved(c, 0.1)]
    r2 = [Retrieved(c, 5.0), Retrieved(a, 4.0), Retrieved(b, 1.0)]
    fused = rrf_fuse([r1, r2], k=60)
    # A aparece alto en ambas -> deberia quedar primero.
    assert fused[0].chunk.id == "A"
    assert {r.chunk.id for r in fused} == {"A", "B", "C"}


def test_rrf_top_n_limits():
    a, b, c = _c("A", "a"), _c("B", "b"), _c("C", "c")
    fused = rrf_fuse([[Retrieved(a, 1), Retrieved(b, 1), Retrieved(c, 1)]], top_n=2)
    assert len(fused) == 2
