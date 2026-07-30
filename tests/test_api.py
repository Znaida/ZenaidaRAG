"""Tests de la API FastAPI (Fase 3) con un engine falso (sin red ni modelo)."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from zenaidarag.api import Engine, create_app
from zenaidarag.config import Settings
from zenaidarag.llm.fake import FakeLLM
from zenaidarag.store import Chunk, Retrieved


class StubStore:
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


def _client(results):
    engine = Engine(
        store=StubStore(results),
        embeddings=StubEmbeddings(),
        llm=FakeLLM(),
        settings=Settings(min_score=0.15),
    )
    return TestClient(create_app(engine=engine))


def _parse_sse(text: str):
    """Parsea el cuerpo SSE en una lista de (event, data)."""
    events = []
    event = None
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            events.append((event, line.split(":", 1)[1].strip()))
    return events


def test_health_reports_index_and_provider():
    client = _client([_res("a", "s.md", 0.9)])
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["indexed_chunks"] == 1


def test_ask_streams_tokens_and_sources():
    client = _client([_res("contexto util sobre perros", "dental.md", 0.9)])
    r = client.post("/ask", json={"question": "algo sobre perros"})
    assert r.status_code == 200
    events = _parse_sse(r.text)
    kinds = [e for e, _ in events]
    assert "token" in kinds
    assert "sources" in kinds
    assert "done" in kinds
    sources_data = next(d for e, d in events if e == "sources")
    assert json.loads(sources_data) == ["dental.md"]


def test_ask_refuses_out_of_domain():
    client = _client([_res("irrelevante", "x.md", 0.01)])
    r = client.post("/ask", json={"question": "capital de Francia"})
    events = _parse_sse(r.text)
    tokens = "".join(d for e, d in events if e == "token")
    assert "no tengo" in tokens.lower()
    sources_data = next(d for e, d in events if e == "sources")
    assert json.loads(sources_data) == []


def test_ask_validates_empty_question():
    client = _client([_res("a", "s.md", 0.9)])
    r = client.post("/ask", json={"question": ""})
    assert r.status_code == 422
