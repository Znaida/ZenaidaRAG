"""Bot de Telegram por long-polling (Fase 5, ADR-008).

Cliente fino sobre la Bot API de Telegram usando httpx (sin dependencias extra).
Reutiliza el motor RAG: cada mensaje de texto se responde con `answer()` y se
envia la respuesta + fuentes. La logica de "update -> texto de respuesta" esta
en `reply_for_message`, testeable sin red.
"""
from __future__ import annotations

import time

import httpx

from zenaidarag.channels import format_reply
from zenaidarag.rag.answer import answer

API_BASE = "https://api.telegram.org/bot{token}/{method}"

WELCOME = (
    "Hola, soy ZenaidaRAG, asistente de apoyo veterinario. "
    "Preguntame sobre los documentos del corpus y te respondo citando fuentes. "
    "Si no tengo informacion suficiente, te lo digo (no invento)."
)


def reply_for_message(text: str, engine) -> str:
    """Dada la pregunta del usuario, devuelve el texto de respuesta del bot."""
    text = (text or "").strip()
    if not text:
        return "Enviame una pregunta de texto."
    if text in ("/start", "/help"):
        return WELCOME
    ans = answer(
        text,
        store=engine.store,
        embeddings=engine.embeddings,
        llm=engine.llm,
        top_k=engine.settings.top_k,
        min_score=engine.settings.min_score,
        fetch_k=engine.settings.fetch_k,
        use_hybrid=engine.settings.use_hybrid,
        reranker=getattr(engine, "reranker", None),
    )
    return format_reply(ans)


class TelegramBot:
    """Cliente de polling minimalista para la Bot API de Telegram."""

    def __init__(self, token: str, engine, timeout: int = 30):
        if not token:
            raise ValueError("Falta TELEGRAM_BOT_TOKEN.")
        self.token = token
        self.engine = engine
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout + 10)

    def _call(self, method: str, **params):
        url = API_BASE.format(token=self.token, method=method)
        resp = self._client.post(url, json=params)
        resp.raise_for_status()
        return resp.json()

    def send_message(self, chat_id: int, text: str) -> None:
        self._call("sendMessage", chat_id=chat_id, text=text)

    def get_updates(self, offset: int | None = None):
        data = self._call("getUpdates", offset=offset, timeout=self.timeout)
        return data.get("result", [])

    def poll_once(self, offset: int | None):
        """Un ciclo de polling tolerante a timeouts (normales en long-polling).

        Devuelve el nuevo offset. Los timeouts de lectura (sin mensajes nuevos)
        NO son un error: se ignoran y se sigue.
        """
        try:
            updates = self.get_updates(offset=offset)
        except httpx.TimeoutException:
            return offset  # sin novedades; el loop reintenta
        for update in updates:
            offset = update["update_id"] + 1
            self.process_update(update)
        return offset

    def process_update(self, update: dict) -> None:
        """Procesa un update: si trae mensaje de texto, responde.

        Un fallo al generar la respuesta (p. ej. error puntual del LLM) no debe
        tumbar el bot: se avisa al usuario y se sigue.
        """
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = message.get("text")
        if chat_id is None or text is None:
            return
        try:
            reply = reply_for_message(text, self.engine)
        except Exception:  # noqa: BLE001 — fallo del LLM/RAG: avisar y continuar
            reply = "Tuve un problema procesando tu pregunta. Intenta de nuevo."
        self.send_message(chat_id, reply)

    def run(self) -> None:  # pragma: no cover — loop de red, se prueba por unidades
        """Loop de polling (bloqueante). Ctrl+C para salir."""
        offset = None
        while True:
            try:
                offset = self.poll_once(offset)
            except httpx.HTTPError:
                # Error de red transitorio: esperar un poco y reintentar.
                time.sleep(3)
