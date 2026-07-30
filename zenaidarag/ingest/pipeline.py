"""Pipeline de ingesta: carpeta -> texto -> chunks -> embeddings -> VectorStore.

Orquesta los loaders (ADR-007), el chunking (ADR-006), los embeddings (ADR-004)
y el vector store (ADR-003). Devuelve estadisticas para dar feedback en la CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zenaidarag.ingest.chunking import chunk_text
from zenaidarag.ingest.loaders import is_supported, load_document


@dataclass
class IngestStats:
    """Resultado de una corrida de ingesta."""

    files_ok: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    chunks: int = 0
    errors: list[str] = field(default_factory=list)


def iter_documents(folder: str | Path):
    """Itera los archivos soportados dentro de `folder` (recursivo)."""
    folder = Path(folder)
    for path in sorted(folder.rglob("*")):
        if path.is_file() and is_supported(path):
            yield path


def ingest_file(
    path: str | Path,
    store,
    embeddings,
    source: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    batch_size: int = 64,
) -> int:
    """Ingiere un solo archivo. Devuelve el nº de chunks indexados.

    `source` es el identificador para citación (por defecto, el nombre del archivo).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    source = source or path.name
    text = load_document(path)
    chunks = chunk_text(text, source, chunk_size, chunk_overlap)
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embeddings.embed_documents([c.text for c in batch])
        store.add(batch, vectors)
    return len(chunks)


def iter_ingest_file(
    path: str | Path,
    store,
    embeddings,
    source: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    batch_size: int = 16,
):
    """Ingiere un archivo emitiendo progreso: yield {'done', 'total'} por lote.

    Permite mostrar una barra de progreso en la UI (documentos grandes tardan).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    source = source or path.name
    text = load_document(path)
    chunks = chunk_text(text, source, chunk_size, chunk_overlap)
    total = len(chunks)
    if total == 0:
        yield {"done": 0, "total": 0}
        return
    done = 0
    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embeddings.embed_documents([c.text for c in batch])
        store.add(batch, vectors)
        done += len(batch)
        yield {"done": done, "total": total}


def ingest_folder(
    folder: str | Path,
    store,
    embeddings,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    root: str | Path | None = None,
    batch_size: int = 64,
) -> IngestStats:
    """Ingiere todos los documentos soportados de `folder` en `store`.

    - `store`: implementacion de VectorStore (p.ej. ChromaStore).
    - `embeddings`: implementacion de Embeddings (p.ej. LocalEmbeddings).
    - `root`: base para calcular la ruta relativa usada como `source` (citacion).
    """
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(folder)
    root = Path(root) if root is not None else folder
    stats = IngestStats()

    for path in iter_documents(folder):
        try:
            source = path.relative_to(root).as_posix()
        except ValueError:
            source = path.name
        try:
            text = load_document(path)
        except Exception as exc:  # noqa: BLE001 — se registra y se continua
            stats.files_failed += 1
            stats.errors.append(f"{source}: {exc}")
            continue

        chunks = chunk_text(text, source, chunk_size, chunk_overlap)
        if not chunks:
            stats.files_skipped += 1
            continue

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vectors = embeddings.embed_documents([c.text for c in batch])
            store.add(batch, vectors)

        stats.files_ok += 1
        stats.chunks += len(chunks)

    return stats
