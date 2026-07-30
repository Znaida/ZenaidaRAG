"""Tests de reranking (con reranker falso) y del motor de evaluacion (Fase 4)."""
from __future__ import annotations

from zenaidarag.evaluate import evaluate
from zenaidarag.rag.answer import select_context
from zenaidarag.store import Chunk, Retrieved


class StubStore:
    def __init__(self, results):
        self._results = results

    def query(self, vector, top_k):
        return self._results[:top_k]

    def get_all(self):
        return [r.chunk for r in self._results]

    def count(self):
        return len(self._results)


class StubEmbeddings:
    def embed_query(self, text):
        return [0.0]

    def embed_documents(self, texts):
        return [[0.0] for _ in texts]


class ReverseReranker:
    """Reranker falso: invierte el orden de los candidatos (para verificar efecto)."""

    def rerank(self, question, candidates, top_k):
        return list(reversed(list(candidates)))[:top_k]


def _res(text, source, score):
    return Retrieved(chunk=Chunk(id=source, text=text, source=source), score=score)


def test_select_context_applies_reranker():
    results = [_res("a", "a.md", 0.9), _res("b", "b.md", 0.8), _res("c", "c.md", 0.7)]
    store = StubStore(results)
    ctx = select_context(
        "q", store, StubEmbeddings(), top_k=2, min_score=0.15, reranker=ReverseReranker()
    )
    # Con el reranker que invierte, el ultimo candidato pasa a ser el primero.
    assert ctx[0].chunk.source == "c.md"
    assert len(ctx) == 2


def test_select_context_refuses_below_threshold():
    store = StubStore([_res("x", "x.md", 0.05)])
    ctx = select_context("q", store, StubEmbeddings(), top_k=2, min_score=0.35)
    assert ctx is None


def test_evaluate_computes_metrics():
    # Store donde la fuente correcta siempre esta primera (score alto).
    results = [_res("dental info", "higiene_dental_canina.md", 0.9)]
    store = StubStore(results)
    cases = [
        {"question": "dientes perro", "expected_source": "higiene_dental_canina.md"},
        {"question": "capital francia", "expected_source": None},
    ]
    res = evaluate(cases, store, StubEmbeddings(), top_k=4, min_score=0.35)
    assert res.hit_at_k == 1.0
    assert res.mrr == 1.0
    # La pregunta abierta: score 0.9 > 0.35 -> NO se niega -> refusal_accuracy 0.
    assert res.refusal_accuracy == 0.0
    assert res.n_grounded == 1 and res.n_open == 1
