"""Tests de los loaders por formato (ADR-007)."""
from __future__ import annotations

from pathlib import Path

import pytest

from zenaidarag.ingest.loaders import (
    UnsupportedFormatError,
    is_supported,
    load_document,
)


def test_supported_detection():
    assert is_supported(Path("a.pdf"))
    assert is_supported(Path("a.MD"))  # case-insensitive
    assert not is_supported(Path("a.exe"))


def test_load_txt_and_md(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Titulo\ncontenido veterinario", encoding="utf-8")
    text = load_document(f)
    assert "veterinario" in text


def test_load_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("animal,dosis\nperro,10\ngato,5\n", encoding="utf-8")
    text = load_document(f)
    assert "perro" in text and "dosis" in text


def test_unsupported_format(tmp_path):
    f = tmp_path / "x.exe"
    f.write_bytes(b"\x00\x01")
    with pytest.raises(UnsupportedFormatError):
        load_document(f)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_document(tmp_path / "no_existe.txt")


def test_sample_docs_load():
    sample = Path("sample_docs")
    if not sample.exists():
        pytest.skip("sample_docs no disponible")
    mds = list(sample.glob("*.md"))
    assert mds, "deberia haber documentos de ejemplo"
    for md in mds:
        assert load_document(md).strip()
