"""Adaptador LLM para Google Gemini (ADR-005). Implementa LLMProvider.

Usa el SDK `google-genai`. La key se pasa por config (GEMINI_API_KEY).
"""
from __future__ import annotations

from collections.abc import Iterator


class GeminiProvider:
    """Proveedor LLM basado en Google Gemini."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise ValueError("Falta GEMINI_API_KEY para usar el proveedor gemini.")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        resp = self._client.models.generate_content(model=self.model, contents=prompt)
        return (resp.text or "").strip()

    def stream(self, prompt: str) -> Iterator[str]:
        stream = self._client.models.generate_content_stream(
            model=self.model, contents=prompt
        )
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if text:
                yield text
