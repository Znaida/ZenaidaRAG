"""CLI de ZenaidaRAG (Typer).

Fase 0: esqueleto con `--help`, `version` y comandos `ingest`/`ask` declarados
(aun no implementados; llegan en Fases 1 y 2). Esto permite verificar que el
paquete instala y expone el ejecutable `zenaidarag`.
"""
from __future__ import annotations

import typer
from rich.console import Console

from zenaidarag import __version__

app = typer.Typer(
    name="zenaidarag",
    help="Asistente RAG de apoyo veterinario: recuperacion semantica con citacion de fuentes.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Muestra la version instalada."""
    console.print(f"ZenaidaRAG v{__version__}")


@app.command()
def ingest(
    carpeta: str = typer.Argument(..., help="Carpeta con documentos a ingerir."),
) -> None:
    """Ingesta documentos (PDF/DOCX/MD/TXT/CSV/XLSX) al indice vectorial."""
    from zenaidarag.config import get_settings
    from zenaidarag.factory import build_embeddings, build_store
    from zenaidarag.ingest.pipeline import ingest_folder

    settings = get_settings()
    console.print(f"Ingiriendo [bold]{carpeta}[/] ...")
    console.print(
        f"  embeddings={settings.embeddings_provider}:{settings.embeddings_model}"
    )
    console.print(f"  store={settings.vector_store} -> {settings.chroma_path}")

    try:
        embeddings = build_embeddings(settings)
        store = build_store(settings)
        stats = ingest_folder(
            carpeta,
            store=store,
            embeddings=embeddings,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
    except FileNotFoundError:
        console.print(f"[red]No existe la carpeta:[/] {carpeta}")
        raise typer.Exit(code=1) from None

    console.print(
        f"[green]Listo.[/] {stats.files_ok} archivo(s) ingeridos, "
        f"{stats.chunks} chunk(s) indexados "
        f"(saltados: {stats.files_skipped}, fallidos: {stats.files_failed})."
    )
    total = getattr(store, "count", lambda: None)()
    if total is not None:
        console.print(f"  Total en el indice: [bold]{total}[/] chunk(s).")
    for err in stats.errors:
        console.print(f"  [yellow]! {err}[/]")


@app.command()
def ask(
    pregunta: str = typer.Argument(..., help="Pregunta a responder con base en el corpus."),
) -> None:
    """Responde una pregunta recuperando fragmentos y citando fuentes."""
    from zenaidarag.config import get_settings
    from zenaidarag.factory import build_embeddings, build_llm, build_store
    from zenaidarag.rag.answer import answer

    settings = get_settings()
    try:
        embeddings = build_embeddings(settings)
        store = build_store(settings)
        llm = build_llm(settings)
    except ValueError as exc:
        console.print(f"[red]Config:[/] {exc}")
        raise typer.Exit(code=1) from None

    if getattr(store, "count", lambda: 1)() == 0:
        console.print(
            "[yellow]El indice esta vacio.[/] Corre primero: "
            "[bold]zenaidarag ingest <carpeta>[/]"
        )
        raise typer.Exit(code=1)

    from zenaidarag.factory import build_reranker

    result = answer(
        pregunta,
        store=store,
        embeddings=embeddings,
        llm=llm,
        top_k=settings.top_k,
        min_score=settings.min_score,
        fetch_k=settings.fetch_k,
        use_hybrid=settings.use_hybrid,
        reranker=build_reranker(settings),
    )

    console.print()
    console.print(result.text)
    if result.sources:
        console.print()
        console.print("[dim]Fuentes:[/] " + ", ".join(result.sources))
    elif result.refused:
        console.print("[dim](sin contexto suficiente en el corpus)[/]")


@app.command()
def eval(
    set_path: str = typer.Option("eval/questions.json", help="Ruta del set de evaluacion."),
) -> None:
    """Evalua la recuperacion (hit@k, MRR, negativa) comparando configuraciones."""
    from rich.table import Table

    from zenaidarag.config import get_settings
    from zenaidarag.evaluate import evaluate, load_cases
    from zenaidarag.factory import build_embeddings, build_reranker, build_store

    settings = get_settings()
    cases = load_cases(set_path)
    embeddings = build_embeddings(settings)
    store = build_store(settings)
    if store.count() == 0:
        console.print("[yellow]Indice vacio. Corre primero:[/] zenaidarag ingest <carpeta>")
        raise typer.Exit(code=1)

    configs = [
        ("baseline (semantico)", {"use_hybrid": False, "reranker": None}),
        ("+ hibrido (BM25)", {"use_hybrid": True, "reranker": None}),
    ]
    if settings.use_rerank:
        rk = build_reranker(settings)
        configs.append(("+ hibrido + rerank", {"use_hybrid": True, "reranker": rk}))
    else:
        console.print("[dim]Tip: USE_RERANK=true para incluir la fila con rerank.[/]")

    table = Table(title=f"Evaluacion de recuperacion ({len(cases)} casos)")
    table.add_column("Configuracion")
    table.add_column("hit@k", justify="right")
    table.add_column("MRR", justify="right")
    table.add_column("negativa", justify="right")

    for name, opts in configs:
        res = evaluate(
            cases, store, embeddings,
            top_k=settings.top_k, min_score=settings.min_score, fetch_k=settings.fetch_k,
            **opts,
        )
        table.add_row(
            name, f"{res.hit_at_k:.0%}", f"{res.mrr:.3f}", f"{res.refusal_accuracy:.0%}"
        )
    console.print(table)


@app.command(name="app")
def desktop() -> None:
    """Abre la app de escritorio ZenaidaVet (ventana + backend juntos). (Fase 7)"""
    from zenaidarag.desktop import run_desktop

    run_desktop()


@app.command()
def telegram() -> None:
    """Corre el bot de Telegram (polling) sobre el mismo motor RAG. (Fase 5)"""
    from zenaidarag.api import build_engine
    from zenaidarag.channels.telegram import TelegramBot
    from zenaidarag.config import get_settings

    settings = get_settings()
    if not settings.telegram_bot_token:
        console.print("[red]Falta TELEGRAM_BOT_TOKEN en el .env.[/]")
        raise typer.Exit(code=1)

    console.print("Construyendo motor RAG...")
    engine = build_engine(settings)
    if getattr(engine.store, "count", lambda: 1)() == 0:
        console.print("[yellow]Indice vacio. Corre primero:[/] zenaidarag ingest <carpeta>")
        raise typer.Exit(code=1)

    bot = TelegramBot(settings.telegram_bot_token, engine)
    console.print("[green]Bot de Telegram en marcha (polling). Ctrl+C para salir.[/]")
    try:
        bot.run()
    except KeyboardInterrupt:
        console.print("\nBot detenido.")


@app.command()
def serve(
    host: str = typer.Option(None, help="Host (por defecto, el de la config)."),
    port: int = typer.Option(None, help="Puerto (por defecto, el de la config)."),
) -> None:
    """Levanta la API FastAPI (POST /ask con SSE, GET /health)."""
    import uvicorn

    from zenaidarag.config import get_settings

    settings = get_settings()
    host = host or settings.api_host
    port = port or settings.api_port
    console.print(f"API en [bold]http://{host}:{port}[/]  (docs: /docs)")
    uvicorn.run("zenaidarag.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
