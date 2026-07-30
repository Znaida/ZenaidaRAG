"""Tests del chunking con solapamiento (ADR-006)."""
from __future__ import annotations

import pytest

from zenaidarag.ingest.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("", "doc.md") == []
    assert chunk_text("   \n  ", "doc.md") == []


def test_single_short_chunk():
    chunks = chunk_text("hola mundo veterinario", "doc.md", chunk_size=800)
    assert len(chunks) == 1
    assert chunks[0].source == "doc.md"
    assert chunks[0].metadata["chunk"] == 0
    assert "veterinario" in chunks[0].text


def test_multiple_chunks_with_overlap():
    text = " ".join(f"palabra{i}" for i in range(300))
    chunks = chunk_text(text, "doc.md", chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1
    # Indices consecutivos y crecientes.
    assert [c.metadata["chunk"] for c in chunks] == list(range(len(chunks)))
    # Ningun chunk excede el tamano objetivo por mucho.
    assert all(len(c.text) <= 200 for c in chunks)


def test_ids_are_unique():
    text = " ".join(f"w{i}" for i in range(500))
    chunks = chunk_text(text, "doc.md", chunk_size=120, chunk_overlap=20)
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))


def test_invalid_params():
    with pytest.raises(ValueError):
        chunk_text("x", "d", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("x", "d", chunk_size=100, chunk_overlap=100)
