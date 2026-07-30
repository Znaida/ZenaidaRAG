"""App de escritorio ZenaidaVet (Fase 7, ADR-012).

Arranca el backend FastAPI en un hilo y muestra la interfaz web en una ventana
nativa (pywebview). Cerrar la ventana (X) o el boton "Apagar" detiene todo.
Backend y frontend se levantan juntos con un solo comando: `zenaidarag app`.
"""
from __future__ import annotations

import socket
import threading
import time

import httpx

from zenaidarag.config import Settings, get_settings


def _find_free_port(preferred: int, host: str = "127.0.0.1") -> int:
    """Devuelve `preferred` si esta libre; si no, un puerto libre cualquiera."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise OSError("No hay puertos libres disponibles.")


def _wait_healthy(url: str, timeout: float = 60.0) -> bool:
    """Espera a que el servidor responda /health."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(url + "/health", timeout=3).status_code == 200:
                return True
        except httpx.HTTPError:
            time.sleep(0.4)
    return False


def run_desktop(settings: Settings | None = None) -> None:  # pragma: no cover — UI/red
    """Levanta backend + ventana nativa. Bloquea hasta que se cierra la ventana."""
    import uvicorn
    import webview

    from zenaidarag.api import build_engine, create_app

    settings = settings or get_settings()
    host = settings.api_host
    port = _find_free_port(settings.api_port, host)
    url = f"http://{host}:{port}"

    # Construir el motor por adelantado (carga el modelo) para que la UI abra lista.
    print("Iniciando ZenaidaVet: cargando motor RAG...")
    engine = build_engine(settings)

    def on_shutdown() -> None:
        for w in list(webview.windows):
            try:
                w.destroy()
            except Exception:  # noqa: BLE001, S110 — cierre best-effort de la ventana
                pass

    app = create_app(engine=engine, on_shutdown=on_shutdown)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not _wait_healthy(url):
        server.should_exit = True
        raise RuntimeError("El backend no respondio a tiempo.")

    # Precargar el modelo de embeddings en segundo plano: la ventana abre ya, con
    # el cartel de "cargando", y la IA se habilita cuando termina (health.ready).
    if hasattr(app.state, "warm_up"):
        app.state.warm_up()

    class JsApi:
        def close(self) -> None:
            on_shutdown()

    webview.create_window(
        "ZenaidaVet", url, js_api=JsApi(), width=1024, height=720, min_size=(820, 560)
    )
    # Icono de la ventana/barra de tareas. En Windows pywebview exige un .ico
    # valido; pasarle otra cosa hace crashear el backend de la UI. Por eso solo
    # se pasa el icono si el .ico existe.
    from pathlib import Path

    icon = Path(__file__).resolve().parent.parent / "assets" / "logo.ico"
    start_kwargs = {"icon": str(icon)} if icon.exists() else {}
    try:
        webview.start(**start_kwargs)  # bloquea hasta cerrar la ventana (X o Apagar)
    except TypeError:  # version de pywebview sin parametro `icon`
        webview.start()

    # Ventana cerrada -> apagar el servidor.
    server.should_exit = True
    thread.join(timeout=5)
