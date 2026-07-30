"""Tests del proveedor Ollama (LLM local) con HTTP mockeado (sin red)."""
from __future__ import annotations

import json

import httpx

from zenaidarag.llm.ollama import OllamaProvider


def _provider_with(handler) -> OllamaProvider:
    """Crea un OllamaProvider con el cliente httpx interceptado por `handler`."""
    p = OllamaProvider(model="llama3", host="http://localhost:11434")
    p._client = httpx.Client(base_url=p.host, transport=httpx.MockTransport(handler))
    return p


def test_generate_returns_response_text():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        body = json.loads(request.content)
        assert body["model"] == "llama3"
        assert body["stream"] is False
        return httpx.Response(200, json={"response": "  Hola mundo  ", "done": True})

    provider = _provider_with(handler)
    assert provider.generate("cualquier prompt") == "Hola mundo"


def test_stream_yields_tokens_until_done():
    lines = [
        {"response": "Hola", "done": False},
        {"response": " ", "done": False},
        {"response": "mundo", "done": False},
        {"response": "", "done": True},
    ]
    ndjson = "\n".join(json.dumps(line) for line in lines).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is True
        return httpx.Response(200, content=ndjson)

    provider = _provider_with(handler)
    assert "".join(provider.stream("x")) == "Hola mundo"


def test_stream_ignora_lineas_no_json():
    # Ollama podria intercalar lineas vacias; no deben romper el parseo.
    payload = b'\n{"response": "ok", "done": false}\n\n{"response": "", "done": true}\n'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    provider = _provider_with(handler)
    assert "".join(provider.stream("x")) == "ok"
