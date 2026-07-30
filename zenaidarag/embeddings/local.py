"""Embeddings locales con sentence-transformers (ADR-004). Costo $0, offline.

El modelo se descarga la primera vez (cache local) y luego corre sin red.
Implementa la interfaz `Embeddings`.
"""
from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    # Import perezoso: sentence-transformers es pesado; solo se carga al usarlo.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class LocalEmbeddings:
    """Embeddings con un modelo local de sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name

    @property
    def _model(self):
        return _load_model(self.model_name)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(
            [text], normalize_embeddings=True, show_progress_bar=False
        )[0]
        return vector.tolist()
