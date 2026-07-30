"""API FastAPI de ZenaidaRAG (Fase 3): POST /ask con streaming SSE + GET /health.

El "engine" (store + embeddings + llm + settings) se inyecta, de modo que la API
sea testeable con dobles de prueba sin cargar modelos ni gastar cuota. En
produccion se construye desde la config via `build_engine()`.
"""
from __future__ import annotations

import json
import threading
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


class SetLLMRequest(BaseModel):
    provider: str = Field(..., description="Proveedor LLM: gemini | openai | ollama | fake")


class SetQualityRequest(BaseModel):
    enabled: bool = Field(..., description="Activar modo calidad (hibrido + reranking).")


def _llm_error_message(provider: str, exc: Exception) -> str:
    """Traduce el fallo al cambiar de proveedor en un mensaje util para el usuario."""
    if provider == "gemini":
        return "Falta o es invalida la GEMINI_API_KEY en .env."
    if provider == "openai":
        return "Falta o es invalida la OPENAI_API_KEY en .env."
    if provider == "ollama":
        return (
            "No se pudo conectar con Ollama. Verifica que este corriendo "
            "(ollama serve) y que el modelo este descargado (ollama pull)."
        )
    return str(exc)


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

    # Por defecto la app arranca "lista" (tests, engines inyectados). La app de
    # escritorio llama a warm_up() para precargar el modelo de embeddings en
    # segundo plano y recien ahi marcar ready=True (evita el freeze en la 1a
    # pregunta, que dispara la carga perezosa del modelo).
    app.state.ready = True
    # Estado del reranker para el indicador de la UI: off | loading | ready.
    app.state.reranker_status = "off"

    def warm_up() -> None:
        app.state.ready = False

        def _run() -> None:
            try:
                get_engine().embeddings.embed_query("calentando el modelo")
            except Exception:  # noqa: BLE001, S110 — best-effort; igual se marca listo
                pass
            finally:
                app.state.ready = True

        threading.Thread(target=_run, daemon=True).start()

    app.state.warm_up = warm_up

    @app.get("/health")
    def health() -> dict:
        from zenaidarag.factory import llm_model_for

        eng = get_engine()
        count = getattr(eng.store, "count", lambda: None)()
        provider = eng.settings.llm_provider
        return {
            "status": "ok",
            "ready": getattr(app.state, "ready", True),
            "reranker": getattr(app.state, "reranker_status", "off"),
            "indexed_chunks": count,
            "llm_provider": provider,
            "llm_model": llm_model_for(provider, eng.settings),
        }

    # Proveedores LLM ofrecidos en el selector de la interfaz.
    LLM_CHOICES = [
        {"id": "gemini", "label": "Gemini (nube)"},
        {"id": "openai", "label": "OpenAI (nube)"},
        {"id": "ollama", "label": "Ollama (local)"},
    ]

    @app.get("/llm")
    def llm_options() -> dict:
        eng = get_engine()
        return {"current": eng.settings.llm_provider, "options": LLM_CHOICES}

    @app.post("/llm")
    def set_llm(req: SetLLMRequest) -> dict:
        """Cambia el proveedor LLM en caliente. No persiste: vale para la sesion."""
        from zenaidarag.factory import build_llm, llm_model_for

        eng = get_engine()
        provider = req.provider
        valid = {c["id"] for c in LLM_CHOICES} | {"fake"}
        if provider not in valid:
            return {"ok": False, "error": f"Proveedor no soportado: {provider}"}

        new_settings = eng.settings.model_copy(update={"llm_provider": provider})
        try:
            new_llm = build_llm(new_settings)
            # Chequeo de disponibilidad para dar feedback inmediato.
            if provider == "ollama":
                import httpx

                httpx.get(f"{new_settings.ollama_host}/api/tags", timeout=3)
        except Exception as exc:  # noqa: BLE001 — se reporta al usuario, no se rompe
            return {"ok": False, "error": _llm_error_message(provider, exc)}

        eng.llm = new_llm
        eng.settings.llm_provider = provider
        return {
            "ok": True,
            "provider": provider,
            "model": llm_model_for(provider, eng.settings),
        }

    @app.get("/quality")
    def quality_state() -> dict:
        eng = get_engine()
        return {"enabled": bool(eng.settings.use_hybrid or eng.reranker is not None)}

    @app.post("/quality")
    def set_quality(req: SetQualityRequest) -> dict:
        """Activa/desactiva hibrido + reranking en caliente (para corpus grandes).

        Hibrido (BM25) es inmediato; el reranker carga un cross-encoder (~450 MB)
        en segundo plano, por eso puede tardar unos segundos en surtir efecto.
        """
        from zenaidarag.factory import build_reranker

        eng = get_engine()
        eng.settings.use_hybrid = req.enabled
        if not req.enabled:
            eng.reranker = None
            app.state.reranker_status = "off"
            return {"ok": True, "enabled": False, "reranker": "off"}

        app.state.reranker_status = "loading"

        def _load_reranker() -> None:
            try:
                s = eng.settings.model_copy(update={"use_rerank": True})
                eng.reranker = build_reranker(s)
                app.state.reranker_status = "ready" if eng.reranker else "off"
            except Exception:  # noqa: BLE001 — si falla, sigue solo con hibrido
                eng.reranker = None
                app.state.reranker_status = "error"

        threading.Thread(target=_load_reranker, daemon=True).start()
        return {"ok": True, "enabled": True, "reranker": "loading"}

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
