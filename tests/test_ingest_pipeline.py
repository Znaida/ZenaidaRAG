"""Test end-to-end de la ingesta con ChromaDB real y embeddings falsos.

Se usa un FakeEmbeddings determinista (sin descargar modelo) para verificar el
cableado completo: loaders -> chunking -> embeddings -> ChromaStore. La calidad
de los embeddings reales se prueba aparte en test_embeddings.py.
"""
from __future__ import annotations

import hashlib

from zenaidarag.ingest.pipeline import ingest_folder
from zenaidarag.store.chroma import ChromaStore


class FakeEmbeddings:
    """Embeddings deterministas de dimension fija, sin dependencias pesadas."""

    dim = 16

    def _vec(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in h[: self.dim]]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


def _make_corpus(folder):
    (folder / "a.md").write_text("Higiene dental canina. Cepillar a diario.", encoding="utf-8")
    (folder / "b.txt").write_text("Vacunacion felina basica y refuerzos.", encoding="utf-8")
    (folder / "ignorar.exe").write_bytes(b"\x00")  # no soportado


def test_ingest_end_to_end(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    _make_corpus(docs)

    store = ChromaStore(path=str(tmp_path / "chroma"), collection_name="test")
    stats = ingest_folder(docs, store=store, embeddings=FakeEmbeddings(), chunk_size=200)

    assert stats.files_ok == 2  # a.md y b.txt (el .exe se ignora)
    assert stats.chunks >= 2
    assert store.count() == stats.chunks


def test_ingest_query_retrieves_relevant(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    _make_corpus(docs)

    emb = FakeEmbeddings()
    store = ChromaStore(path=str(tmp_path / "chroma"), collection_name="test")
    ingest_folder(docs, store=store, embeddings=emb, chunk_size=200)

    results = store.query(emb.embed_query("Higiene dental canina. Cepillar a diario."), top_k=1)
    assert results
    assert results[0].chunk.source == "a.md"


def test_ingest_missing_folder(tmp_path):
    store = ChromaStore(path=str(tmp_path / "chroma"), collection_name="test")
    try:
        ingest_folder(tmp_path / "no_existe", store=store, embeddings=FakeEmbeddings())
        raise AssertionError("deberia lanzar FileNotFoundError")
    except FileNotFoundError:
        pass
