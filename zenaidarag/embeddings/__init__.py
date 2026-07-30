"""Interfaz de embeddings (ADR-004). Implementaciones concretas llegan en Fase 1."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Embeddings(Protocol):
    """Convierte texto en vectores. Local por defecto (sentence-transformers)."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Vectoriza una lista de textos (para ingesta)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Vectoriza una consulta individual (para recuperacion)."""
        ...
