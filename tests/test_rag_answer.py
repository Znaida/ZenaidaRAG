"""Tests del flujo RAG (recuperar -> prompt -> responder) con dobles de prueba."""
from __future__ import annotations

from zenaidarag.llm.fake import FakeLLM
from zenaidarag.rag.answer import answer, answer_stream
from zenaidarag.rag.prompt import REFUSAL
from zenaidarag.store import Chunk, Retrieved


class StubStore:
    """VectorStore falso: devuelve resultados fijos con score configurable."""

    def __init__(self, results):
        self._results = results

    def query(self, vector, top_k):
        return self._results[:top_k]

    def count(self):
        return len(self._results)


class StubEmbeddings:
    def embed_query(self, text):
        return [0.0]

    def embed_documents(self, texts):
        return [[0.0] for _ in texts]


def _res(text, source, score):
    return Retrieved(chunk=Chunk(id=source, text=text, source=source), score=score)


def test_answer_with_relevant_context_cites_sources():
    store = StubStore([_res("Cepillar a diario", "dental.md", 0.8)])
    result = answer("pregunta", store, StubEmbeddings(), FakeLLM(), min_score=0.15)
    assert not result.refused
    assert result.sources == ["dental.md"]
    assert "Fuentes" in result.text


def test_answer_refuses_when_scores_below_threshold():
    store = StubStore([_res("algo irrelevante", "x.md", 0.05)])
    result = answer("pregunta", store, StubEmbeddings(), FakeLLM(), min_score=0.15)
    assert result.refused
    assert result.text == REFUSAL
    assert result.sources == []


def test_answer_refuses_when_no_results():
    store = StubStore([])
    result = answer("pregunta", store, StubEmbeddings(), FakeLLM(), min_score=0.15)
    assert result.refused


def test_answer_dedupes_sources():
    store = StubStore([
        _res("a", "same.md", 0.9),
        _res("b", "same.md", 0.8),
        _res("c", "other.md", 0.7),
    ])
    result = answer("q", store, StubEmbeddings(), FakeLLM(), top_k=3, min_score=0.15)
    assert result.sources == ["same.md", "other.md"]


def test_answer_stream_yields_tokens_and_sources():
    store = StubStore([_res("contexto util", "s.md", 0.9)])
    tokens, sources = answer_stream("q", store, StubEmbeddings(), FakeLLM(), min_score=0.15)
    joined = "".join(tokens)
    assert joined.strip()
    assert sources == ["s.md"]


def test_answer_stream_refuses_without_context():
    store = StubStore([])
    tokens, sources = answer_stream("q", store, StubEmbeddings(), FakeLLM())
    assert "".join(tokens) == REFUSAL
    assert sources == []
