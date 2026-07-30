"""Construccion de componentes (embeddings, store) desde la configuracion.

Centraliza la eleccion de implementacion segun los ADR, para que la CLL y la
API no dependan de clases concretas.
"""
from __future__ import annotations

from zenaidarag.config import Settings, get_settings


def build_embeddings(settings: Settings | None = None):
    """Devuelve una implementacion de Embeddings segun la config (ADR-004)."""
    settings = settings or get_settings()
    if settings.embeddings_provider == "local":
        from zenaidarag.embeddings.local import LocalEmbeddings

        return LocalEmbeddings(settings.embeddings_model)
    raise ValueError(f"embeddings_provider no soportado: {settings.embeddings_provider}")


def build_reranker(settings: Settings | None = None):
    """Devuelve un reranker si use_rerank esta activo, si no None (ADR-011)."""
    settings = settings or get_settings()
    if not settings.use_rerank:
        return None
    from zenaidarag.rag.rerank import CrossEncoderReranker

    return CrossEncoderReranker(settings.rerank_model)


def build_llm(settings: Settings | None = None):
    """Devuelve una implementacion de LLMProvider segun la config (ADR-005)."""
    settings = settings or get_settings()
    provider = settings.llm_provider
    if provider == "gemini":
        from zenaidarag.llm.gemini import GeminiProvider

        return GeminiProvider(settings.gemini_api_key, settings.llm_model)
    if provider == "openai":
        from zenaidarag.llm.openai import OpenAIProvider

        return OpenAIProvider(settings.openai_api_key, settings.llm_model)
    if provider == "ollama":
        from zenaidarag.llm.ollama import OllamaProvider

        return OllamaProvider(model=settings.ollama_model, host=settings.ollama_host)
    if provider == "fake":
        from zenaidarag.llm.fake import FakeLLM

        return FakeLLM()
    raise ValueError(f"llm_provider no soportado: {provider}")


def llm_model_for(provider: str, settings: Settings) -> str:
    """Nombre de modelo a mostrar segun el proveedor (para el header/health)."""
    if provider == "ollama":
        return settings.ollama_model
    if provider == "fake":
        return "fake"
    return settings.llm_model  # gemini / openai


def build_store(settings: Settings | None = None):
    """Devuelve una implementacion de VectorStore segun la config (ADR-003)."""
    settings = settings or get_settings()
    if settings.vector_store == "chroma":
        from zenaidarag.store.chroma import ChromaStore

        return ChromaStore(settings.chroma_path, settings.collection_name)
    raise ValueError(f"vector_store no soportado: {settings.vector_store}")
