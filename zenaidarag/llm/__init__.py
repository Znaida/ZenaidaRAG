"""Interfaz LLMProvider (ADR-005). OpenAI por defecto; adaptadores en Fase 2."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class LLMProvider(Protocol):
    """Genera respuestas a partir de un prompt. Provider-agnostico."""

    def generate(self, prompt: str) -> str:
        """Devuelve la respuesta completa."""
        ...

    def stream(self, prompt: str) -> Iterator[str]:
        """Devuelve la respuesta token a token (para SSE en Fase 3)."""
        ...
