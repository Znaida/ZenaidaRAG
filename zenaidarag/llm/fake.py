"""Proveedor LLM falso, determinista y sin red (para tests y demos offline).

Devuelve un eco del prompt de forma controlada; util para probar el cableado
del RAG sin depender de una API externa (ADR-005: testeable con un proveedor
falso).
"""
from __future__ import annotations

from collections.abc import Iterator


class FakeLLM:
    """LLM de prueba: responde con un texto derivado del prompt."""

    def __init__(self, canned: str | None = None):
        self.canned = canned

    def generate(self, prompt: str) -> str:
        if self.canned is not None:
            return self.canned
        # Responde citando que recibio contexto (para asserts en tests).
        tiene_contexto = "(sin fragmentos relevantes)" not in prompt
        if tiene_contexto:
            return "Respuesta de prueba basada en el contexto. Fuentes: [test]."
        return "No tengo informacion suficiente en los documentos para responder eso."

    def stream(self, prompt: str) -> Iterator[str]:
        for token in self.generate(prompt).split(" "):
            yield token + " "
