"""Chunking con solapamiento + metadatos de fuente (ADR-006).

Divide el texto en fragmentos de tamano aproximado `chunk_size` (en caracteres)
con un solapamiento de `chunk_overlap` entre fragmentos consecutivos, para no
perder contexto en los limites. Se intenta cortar en frontera de espacio para
no partir palabras.
"""
from __future__ import annotations

import hashlib
import re

from zenaidarag.store import Chunk

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _chunk_id(source: str, index: int, text: str) -> str:
    h = hashlib.sha1(f"{source}:{index}:{text}".encode()).hexdigest()[:16]
    return f"{source}::{index}::{h}"


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    """Parte `text` en Chunks con solapamiento.

    - `source`: identificador del documento origen (para citacion).
    - `chunk_size`: tamano objetivo en caracteres.
    - `chunk_overlap`: caracteres compartidos entre chunks vecinos.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size debe ser > 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap debe estar en [0, chunk_size)")

    text = _normalize(text)
    if not text:
        return []

    step = chunk_size - chunk_overlap
    chunks: list[Chunk] = []
    start = 0
    index = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        # Intentar cortar en un espacio cercano al final (no partir palabra).
        if end < n:
            space = text.rfind(" ", start + step, end)
            if space != -1:
                end = space
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    id=_chunk_id(source, index, piece),
                    text=piece,
                    source=source,
                    metadata={"source": source, "chunk": index},
                )
            )
            index += 1
        if end >= n:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks
