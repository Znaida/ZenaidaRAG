"""Canales opcionales (Fase 5, ADR-008): Telegram (polling) y Teams (webhook).

Ambos reutilizan el MISMO motor RAG (recuperacion + citacion + negativa honesta);
un canal solo traduce mensajes entrantes/salientes. La logica de "pregunta ->
respuesta con fuentes" es comun y esta en `format_reply`.
"""
from __future__ import annotations

from zenaidarag.rag.answer import Answer


def format_reply(ans: Answer) -> str:
    """Convierte un Answer del RAG en el texto a enviar por un canal."""
    if ans.refused or not ans.sources:
        return ans.text
    fuentes = ", ".join(ans.sources)
    return f"{ans.text}\n\nFuentes: {fuentes}"
