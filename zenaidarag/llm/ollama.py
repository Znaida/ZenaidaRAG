"""Adaptador LLM para Ollama local (ADR-005). Implementa LLMProvider.

Habla con un servidor Ollama corriendo en la propia maquina (por defecto
http://localhost:11434) via su API HTTP. Permite correr el RAG **100% local**,
sin enviar la pregunta ni el contexto a la nube.

Requisitos: tener Ollama instalado y el modelo descargado, por ejemplo:
    ollama pull llama3
"""
from __future__ import annotations

import json
from collections.abc import Iterator

import httpx


class OllamaProvider:
    """Proveedor LLM basado en un servidor Ollama local."""

    def __init__(
        self,
        model: str = "llama3",
        host: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        self.model = model
        self.host = host.rstrip("/")
        # Cliente inyectable para tests (httpx.MockTransport).
        self._client = httpx.Client(base_url=self.host, timeout=timeout)

    def _payload(self, prompt: str, stream: bool) -> dict:
        return {"model": self.model, "prompt": prompt, "stream": stream}

    def generate(self, prompt: str) -> str:
        resp = self._client.post("/api/generate", json=self._payload(prompt, False))
        resp.raise_for_status()
        return (resp.json().get("response") or "").strip()

    def stream(self, prompt: str) -> Iterator[str]:
        # Ollama devuelve NDJSON: una linea JSON por token, con "done" al final.
        with self._client.stream(
            "POST", "/api/generate", json=self._payload(prompt, True)
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = data.get("response")
                if token:
                    yield token
                if data.get("done"):
                    break
