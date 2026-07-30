"""API FastAPI de ZenaidaRAG (Fase 3): POST /ask con streaming SSE + GET /health.

El "engine" (store + embeddings + llm + settings) se inyecta, de modo que la API
sea testeable con dobles de prueba sin cargar modelos ni gastar cuota. En
produccion se construye desde la config via `build_engine()`.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from zenaidarag.config import Settings, get_settings
from zenaidarag.rag.answer import answer_stream
from zenaidarag.webui import index_page

# Logo (isotipo de la zenaida) servido desde assets/ para el header y el favicon.
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"


@dataclass
class Engine:
    """Componentes del RAG ya construidos."""

    store: object
    embeddings: object
    llm: object
    settings: Settings
    reranker: object = None


def build_engine(settings: Settings | None = None) -> Engine:
    """Construye el engine desde la configuracion (ADR-003/004/005/011)."""
    from zenaidarag.factory import (
        build_embeddings,
        build_llm,
        build_reranker,
        build_store,
    )

    settings = settings or get_settings()
    return Engine(
        store=build_store(settings),
        embeddings=build_embeddings(settings),
        llm=build_llm(settings),
        settings=settings,
        reranker=build_reranker(settings),
    )


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta a responder.")


def create_app(
    engine: Engine | None = None, on_shutdown: Callable[[], None] | None = None
) -> FastAPI:
    """Crea la app FastAPI. Si no se pasa engine, se construye perezosamente.

    `on_shutdown`: callback opcional para el endpoint POST /shutdown (lo usa la
    app de escritorio para cerrar la ventana y el servidor).
    """
    app = FastAPI(
        title="ZenaidaRAG",
        description="Asistente RAG de apoyo veterinario con citacion de fuentes.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_engine() -> Engine:
        # Cache perezoso en el estado de la app (evita reconstruir por request).
        if engine is not None:
            return engine
        if not hasattr(app.state, "engine"):
            app.state.engine = build_engine()
        return app.state.engine

    @app.get("/health")
    def health() -> dict:
        eng = get_engine()
        count = getattr(eng.store, "count", lambda: None)()
        return {
            "status": "ok",
            "indexed_chunks": count,
            "llm_provider": eng.settings.llm_provider,
            "llm_model": eng.settings.llm_model,
        }

    @app.post("/ask")
    async def ask(req: AskRequest):
        eng = get_engine()
        tokens, sources = answer_stream(
            req.question,
            store=eng.store,
            embeddings=eng.embeddings,
            llm=eng.llm,
            top_k=eng.settings.top_k,
            min_score=eng.settings.min_score,
            fetch_k=eng.settings.fetch_k,
            use_hybrid=eng.settings.use_hybrid,
            reranker=eng.reranker,
        )

        async def event_generator():
            for tok in tokens:
                yield {"event": "token", "data": tok}
            # Evento final con las fuentes citadas (JSON).
            yield {"event": "sources", "data": json.dumps(sources, ensure_ascii=False)}
            yield {"event": "done", "data": ""}

        return EventSourceResponse(event_generator())

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return index_page()

    @app.get("/logo.png")
    def logo() -> FileResponse:
        """Sirve el isotipo (header + favicon). 404 si falta el archivo."""
        return FileResponse(LOGO_PATH, media_type="image/png")

    @app.get("/documents")
    def list_documents() -> list[dict]:
        eng = get_engine()
        srcs = eng.store.sources() if hasattr(eng.store, "sources") else []
        return [{"source": s, "chunks": n} for s, n in srcs]

    @app.post("/documents/upload")
    async def upload_documents(files: list[UploadFile] = File(...)) -> dict:  # noqa: B008
        """Guarda los archivos en data/docs (sin ingerir). Devuelve nombres."""
        from zenaidarag.ingest.loaders import is_supported

        docs_dir = Path("data/docs")
        docs_dir.mkdir(parents=True, exist_ok=True)
        saved, skipped = [], []
        for up in files:
            name = Path(up.filename or "archivo").name
            dest = docs_dir / name
            if not is_supported(dest):
                skipped.append(name)
                continue
            dest.write_bytes(await up.read())
            saved.append(name)
        return {"saved": saved, "skipped": skipped}

    @app.get("/documents/ingest")
    async def ingest_document(name: str):
        """Ingiere un archivo ya subido, emitiendo progreso por SSE."""
        from zenaidarag.ingest.pipeline import iter_ingest_file

        eng = get_engine()
        path = Path("data/docs") / Path(name).name

        async def gen():
            if not path.exists():
                yield {"event": "error", "data": "El archivo no existe."}
                return
            try:
                last_total = 0
                for p in iter_ingest_file(
                    path, eng.store, eng.embeddings, source=path.name,
                    chunk_size=eng.settings.chunk_size,
                    chunk_overlap=eng.settings.chunk_overlap,
                ):
                    last_total = p["total"]
                    pct = int(p["done"] * 100 / p["total"]) if p["total"] else 100
                    yield {
                        "event": "progress",
                        "data": json.dumps({**p, "percent": pct, "name": path.name}),
                    }
                yield {"event": "done", "data": json.dumps({"name": path.name, "chunks": last_total})}
            except Exception as exc:  # noqa: BLE001
                yield {"event": "error", "data": str(exc)}

        return EventSourceResponse(gen())

    @app.delete("/documents")
    def delete_document(source: str) -> dict:
        """Elimina un documento del índice y su archivo en data/docs."""
        eng = get_engine()
        removed = (
            eng.store.delete_source(source)
            if hasattr(eng.store, "delete_source")
            else 0
        )
        f = Path("data/docs") / Path(source).name
        if f.exists():
            f.unlink()
        return {"deleted": source, "chunks_removed": removed}

    @app.post("/shutdown")
    def shutdown() -> dict:
        if on_shutdown is not None:
            on_shutdown()
        return {"status": "shutting_down"}

    return app


# App por defecto para `uvicorn zenaidarag.api:app`.
app = create_app()
