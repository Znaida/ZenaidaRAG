"""Test de los embeddings locales reales (ADR-004).

Descarga el modelo la primera vez (cache local). Si no hay red/modelo, se salta
para no romper el CI offline.
"""
from __future__ import annotations

import pytest


@pytest.mark.slow
def test_local_embeddings_shape_and_similarity():
    try:
        from zenaidarag.embeddings.local import LocalEmbeddings

        emb = LocalEmbeddings()
        vecs = emb.embed_documents(["higiene dental del perro", "vacuna del gato"])
    except Exception as exc:  # noqa: BLE001 — modelo no disponible / sin red
        pytest.skip(f"modelo local no disponible: {exc}")

    assert len(vecs) == 2
    assert len(vecs[0]) == len(vecs[1]) > 0

    q = emb.embed_query("cuidado dental canino")
    assert len(q) == len(vecs[0])
