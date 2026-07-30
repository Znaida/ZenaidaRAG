"""VectorStore sobre ChromaDB persistente local (ADR-003).

Implementa la interfaz `VectorStore`. Guarda el indice en disco (`chroma_path`)
para que sobreviva entre ejecuciones. Los vectores se calculan afuera (interfaz
`Embeddings`); aqui solo se almacenan y consultan.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from zenaidarag.store import Chunk, Retrieved


class ChromaStore:
    """Almacen vectorial persistente basado en ChromaDB."""

    def __init__(self, path: str = "data/chroma", collection_name: str = "zenaidarag"):
        import chromadb

        Path(path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=path)
        # cosine: coherente con embeddings normalizados (LocalEmbeddings).
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunks y vectors deben tener la misma longitud")
        self._collection.add(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=[list(v) for v in vectors],
            metadatas=[{**c.metadata, "source": c.source} for c in chunks],
        )

    def query(self, vector: list[float], top_k: int) -> list[Retrieved]:
        res = self._collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        out: list[Retrieved] = []
        for cid, text, meta, dist in zip(ids, docs, metas, dists):
            meta = meta or {}
            chunk = Chunk(
                id=cid,
                text=text,
                source=str(meta.get("source", "desconocido")),
                metadata=dict(meta),
            )
            # distancia coseno -> similitud en [0, 1] aprox.
            out.append(Retrieved(chunk=chunk, score=1.0 - float(dist)))
        return out

    def count(self) -> int:
        """Cantidad de chunks indexados (util para tests y feedback en CLI)."""
        return self._collection.count()

    def delete_source(self, source: str) -> int:
        """Elimina todos los chunks de un documento. Devuelve cuántos borró."""
        before = self._collection.count()
        self._collection.delete(where={"source": source})
        return before - self._collection.count()

    def sources(self) -> list[tuple[str, int]]:
        """Lista (fuente, nº de chunks) de los documentos indexados, ordenada."""
        res = self._collection.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in res.get("metadatas", []) or []:
            src = str((meta or {}).get("source", "desconocido"))
            counts[src] = counts.get(src, 0) + 1
        return sorted(counts.items())

    def get_all(self) -> list[Chunk]:
        """Devuelve todos los chunks indexados (para BM25 en busqueda hibrida)."""
        res = self._collection.get(include=["documents", "metadatas"])
        ids = res.get("ids", [])
        docs = res.get("documents", []) or []
        metas = res.get("metadatas", []) or []
        out: list[Chunk] = []
        for cid, text, meta in zip(ids, docs, metas):
            meta = meta or {}
            out.append(
                Chunk(
                    id=cid,
                    text=text or "",
                    source=str(meta.get("source", "desconocido")),
                    metadata=dict(meta),
                )
            )
        return out
