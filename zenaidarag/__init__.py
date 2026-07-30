"""ZenaidaRAG — Asistente RAG de apoyo veterinario."""

import os as _os
from pathlib import Path as _Path

__version__ = "0.1.0"

# Guardar los modelos (embeddings, cross-encoder) JUNTO al proyecto, no en C:.
# Por defecto usa <proyecto>/models. Se puede sobreescribir con HF_HOME o
# ZENAIDA_MODELS_DIR en el entorno. Debe hacerse ANTES de importar
# sentence-transformers / huggingface (por eso va aca, en el __init__).
if not _os.environ.get("HF_HOME"):
    _models = _os.environ.get("ZENAIDA_MODELS_DIR") or str(
        _Path(__file__).resolve().parent.parent / "models"
    )
    _os.environ["HF_HOME"] = _models
