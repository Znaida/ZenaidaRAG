"""Tests de la interfaz de escritorio (Fase 7): pagina, documentos, apagado."""
from __future__ import annotations

from fastapi.testclient import TestClient

from zenaidarag.api import Engine, create_app
from zenaidarag.config import Settings
from zenaidarag.desktop import _find_free_port
from zenaidarag.llm.fake import FakeLLM
from zenaidarag.store import Chunk


class RecordingStore:
    """Store falso en memoria: registra chunks agregados y lista fuentes."""

    def __init__(self):
        self._chunks: list[Chunk] = []

    def add(self, chunks, vectors):
        self._chunks.extend(chunks)

    def query(self, vector, top_k):
        return []

    def count(self):
        return len(self._chunks)

    def sources(self):
        counts: dict[str, int] = {}
        for c in self._chunks:
            counts[c.source] = counts.get(c.source, 0) + 1
        return sorted(counts.items())

    def delete_source(self, source):
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.source != source]
        return before - len(self._chunks)


class StubEmbeddings:
    def embed_query(self, text):
        return [0.0]

    def embed_documents(self, texts):
        return [[0.0] for _ in texts]


def _client(store=None, on_shutdown=None):
    engine = Engine(
        store=store or RecordingStore(),
        embeddings=StubEmbeddings(),
        llm=FakeLLM(),
        settings=Settings(),
    )
    return TestClient(create_app(engine=engine, on_shutdown=on_shutdown))


def test_index_serves_html():
    r = _client().get("/")
    assert r.status_code == 200
    assert "ZenaidaVet" in r.text
    assert "text/html" in r.headers["content-type"]


def test_documents_empty_then_listed():
    store = RecordingStore()
    store.add([Chunk(id="1", text="a", source="doc.md")], [[0.0]])
    r = _client(store).get("/documents")
    assert r.status_code == 200
    assert r.json() == [{"source": "doc.md", "chunks": 1}]


def test_upload_saves_supported_and_skips_rest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # data/docs se crea aca, no en el repo
    client = _client()
    files = [
        ("files", ("nota.md", b"# Titulo\nContenido de prueba.", "text/markdown")),
        ("files", ("virus.exe", b"\x00\x01", "application/octet-stream")),
    ]
    r = client.post("/documents/upload", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["saved"] == ["nota.md"]
    assert body["skipped"] == ["virus.exe"]
    assert (tmp_path / "data" / "docs" / "nota.md").exists()


def test_ingest_streams_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = RecordingStore()
    client = _client(store)
    # Subir primero.
    client.post("/documents/upload", files=[
        ("files", ("nota.md", b"# Titulo\nContenido veterinario de prueba.", "text/markdown"))
    ])
    r = client.get("/documents/ingest", params={"name": "nota.md"})
    assert r.status_code == 200
    assert "progress" in r.text
    assert "done" in r.text
    assert store.count() >= 1


def test_delete_document_removes_chunks():
    store = RecordingStore()
    store.add([Chunk(id="1", text="a", source="doc.md")], [[0.0]])
    store.add([Chunk(id="2", text="b", source="otro.md")], [[0.0]])
    client = _client(store)
    r = client.delete("/documents", params={"source": "doc.md"})
    assert r.status_code == 200
    assert r.json()["chunks_removed"] == 1
    assert store.sources() == [("otro.md", 1)]


def test_shutdown_calls_callback():
    called = {"v": False}

    def cb():
        called["v"] = True

    r = _client(on_shutdown=cb).post("/shutdown")
    assert r.status_code == 200
    assert called["v"] is True


def test_find_free_port_returns_int():
    port = _find_free_port(0)
    assert isinstance(port, int) and port > 0
