"""Configuracion central de ZenaidaRAG (leida de .env / entorno).

Ver `.env.example` para el detalle de cada variable. Los valores por defecto
reflejan los ADR: embeddings locales (ADR-004), ChromaDB local (ADR-003),
OpenAI como LLM por defecto (ADR-005).
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM (ADR-005). provider: gemini | openai | ollama | fake
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    # Ollama (LLM local, sin nube). Requiere un servidor Ollama corriendo.
    ollama_host: str = "http://localhost:11434"

    # Umbral minimo de similitud para considerar que hay contexto util.
    # Por debajo, se responde con negativa honesta (ADR-006).
    min_score: float = 0.35

    # Embeddings (ADR-004)
    embeddings_provider: str = "local"
    # Multilingue por defecto: corpus en espanol (ver ADR-004, nota 2026-07-28).
    embeddings_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Vector store (ADR-003)
    vector_store: str = "chroma"
    chroma_path: str = "data/chroma"
    collection_name: str = "zenaidarag"

    # Ingesta / recuperacion
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4

    # Calidad de recuperacion (Fase 4, ADR-011). Opcionales, off por defecto.
    use_hybrid: bool = False  # fusion semantica + BM25 (keyword)
    use_rerank: bool = False  # reordenamiento con cross-encoder
    fetch_k: int = 12  # candidatos a recuperar antes de rerank/fusion
    rerank_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"  # multilingue

    # API (Fase 3)
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Canales (Fase 5, ADR-008). Opcionales.
    telegram_bot_token: str = ""


def get_settings() -> Settings:
    """Devuelve la configuracion cargada desde entorno/.env."""
    return Settings()
