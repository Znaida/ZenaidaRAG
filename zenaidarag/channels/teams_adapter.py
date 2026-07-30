"""Adaptador Teams / Bot Framework por webhook (Fase 5, ADR-008).

DOCUMENTADO, no requiere despliegue. Microsoft Teams (via Azure Bot Service /
Bot Framework) envia "Activities" JSON a un endpoint HTTPS y espera una Activity
de respuesta. Aqui se traduce Activity entrante -> RAG -> Activity saliente,
reutilizando el mismo motor.

Para desplegarlo de verdad harian falta (fuera de v1):
  1. Registrar un Azure Bot y obtener AppId/AppPassword.
  2. Exponer `/api/messages` por HTTPS (o via ngrok en desarrollo).
  3. Validar el token JWT del Bot Framework en cada request (seguridad).
Este modulo deja la logica de negocio lista; la infra queda documentada.
"""
from __future__ import annotations

from zenaidarag.channels import format_reply
from zenaidarag.rag.answer import answer


def handle_activity(activity: dict, engine) -> dict:
    """Traduce una Activity de Bot Framework a la Activity de respuesta.

    Solo maneja actividades de tipo 'message'; para otras devuelve una Activity
    vacia de tipo 'message' sin texto (el conector la ignora).
    """
    if activity.get("type") != "message":
        return {"type": "message"}

    question = (activity.get("text") or "").strip()
    if not question:
        return {"type": "message", "text": "Enviame una pregunta de texto."}

    ans = answer(
        question,
        store=engine.store,
        embeddings=engine.embeddings,
        llm=engine.llm,
        top_k=engine.settings.top_k,
        min_score=engine.settings.min_score,
        fetch_k=engine.settings.fetch_k,
        use_hybrid=engine.settings.use_hybrid,
        reranker=getattr(engine, "reranker", None),
    )
    return {"type": "message", "text": format_reply(ans)}
