"""Adaptador LLM para OpenAI (ADR-005, opcional). Implementa LLMProvider."""
from __future__ import annotations

from collections.abc import Iterator


class OpenAIProvider:
    """Proveedor LLM basado en OpenAI (Chat Completions)."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("Falta OPENAI_API_KEY para usar el proveedor openai.")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model

    def _messages(self, prompt: str):
        return [{"role": "user", "content": prompt}]

    def generate(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model, messages=self._messages(prompt)
        )
        return (resp.choices[0].message.content or "").strip()

    def stream(self, prompt: str) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.model, messages=self._messages(prompt), stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
