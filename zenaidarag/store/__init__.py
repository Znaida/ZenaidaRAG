"""Interfaz VectorStore (ADR-003). Impl ChromaDB local llega en Fase 1."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Chunk:
    """Fragmento de documento con su texto y metadatos de fuente."""

    id: str
    text: str
    source: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Retrieved:
    """Chunk recuperado con su score de similitud."""

    chunk: Chunk
    score: float


class VectorStore(Protocol):
    """Almacena y recupera chunks por similitud semantica."""

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[list[float]]) -> None:
        """Indexa chunks con sus vectores."""
        ...

    def query(self, vector: list[float], top_k: int) -> list[Retrieved]:
        """Devuelve los top_k chunks mas similares al vector de consulta."""
        ...
