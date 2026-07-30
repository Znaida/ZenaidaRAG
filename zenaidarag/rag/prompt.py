"""Construccion del prompt RAG con citacion + negativa honesta (ADR-006).

El prompt es el nucleo anti-alucinacion: obliga al modelo a responder SOLO con
base en el contexto recuperado, a citar las fuentes, y a decir explicitamente
que no tiene informacion suficiente cuando el contexto no cubre la pregunta.
Critico en dominio veterinario.
"""
from __future__ import annotations

from collections.abc import Sequence

from zenaidarag.store import Retrieved

# Frase canonica de negativa (se testea de forma laxa: subcadena "no tengo").
REFUSAL = "No tengo informacion suficiente en los documentos para responder eso."

SYSTEM_INSTRUCTIONS = """\
Eres ZenaidaRAG, un asistente de apoyo veterinario. Respondes preguntas usando
UNICAMENTE la informacion del CONTEXTO proporcionado (fragmentos de documentos).

Reglas estrictas:
1. Usa solo el CONTEXTO. No inventes datos, dosis, ni afirmaciones que no esten
   respaldadas por los fragmentos.
2. Si el CONTEXTO no contiene informacion suficiente para responder, responde
   exactamente: "{refusal}"
3. Responde solo con el contenido. NO agregues una linea de "Fuentes:" al final;
   la aplicacion agrega las fuentes por separado.
4. Se claro y conciso. Recuerda que es apoyo informativo, no reemplaza el
   criterio de un medico veterinario.
"""


def format_context(chunks: Sequence[Retrieved]) -> str:
    """Formatea los fragmentos recuperados con su fuente, para el prompt."""
    bloques = []
    for i, r in enumerate(chunks, start=1):
        bloques.append(f"[Fragmento {i} | fuente: {r.chunk.source}]\n{r.chunk.text}")
    return "\n\n".join(bloques)


def build_prompt(question: str, chunks: Sequence[Retrieved]) -> str:
    """Arma el prompt final (instrucciones + contexto + pregunta).

    Si no hay chunks, igual se construye el prompt: las instrucciones obligan a
    responder con la negativa honesta.
    """
    system = SYSTEM_INSTRUCTIONS.format(refusal=REFUSAL)
    contexto = format_context(chunks) if chunks else "(sin fragmentos relevantes)"
    return (
        f"{system}\n\n"
        f"=== CONTEXTO ===\n{contexto}\n\n"
        f"=== PREGUNTA ===\n{question}\n\n"
        f"=== RESPUESTA ==="
    )
