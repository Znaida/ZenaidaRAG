"""Evaluacion de la calidad de recuperacion (Fase 4, ADR-011).

Mide, sobre un set de preguntas con la fuente esperada:
- hit@k: la fuente correcta aparece entre los top_k recuperados.
- MRR: 1/rango de la primera aparicion de la fuente correcta (0 si no aparece).
- negativa: para preguntas de dominio abierto (expected_source=null), acierta si
  el sistema se niega (ningun candidato supera el umbral).

No usa el LLM: evalua solo recuperacion, sin consumir cuota.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from zenaidarag.rag.answer import select_context
from zenaidarag.rag.retrieve import filter_by_score, retrieve


@dataclass
class EvalResult:
    hit_at_k: float
    mrr: float
    refusal_accuracy: float
    n_grounded: int
    n_open: int


def load_cases(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["cases"]


def _first_rank(sources: list[str], expected: str) -> int:
    for i, s in enumerate(sources, start=1):
        if s == expected:
            return i
    return 0


def evaluate(
    cases: list[dict],
    store,
    embeddings,
    top_k: int = 4,
    min_score: float = 0.35,
    fetch_k: int = 12,
    use_hybrid: bool = False,
    reranker=None,
) -> EvalResult:
    """Corre el set y devuelve las metricas agregadas."""
    hits = 0
    rr_sum = 0.0
    grounded = 0
    open_ok = 0
    open_total = 0

    for case in cases:
        q = case["question"]
        expected = case.get("expected_source")

        if expected is None:
            open_total += 1
            # Acierta si se niega: ningun candidato supera el umbral semantico.
            candidates = retrieve(q, store, embeddings, max(fetch_k, top_k))
            if not filter_by_score(candidates, min_score):
                open_ok += 1
            continue

        grounded += 1
        ctx = select_context(
            q, store, embeddings, top_k, min_score, fetch_k, use_hybrid, reranker
        )
        sources = []
        if ctx:
            for r in ctx:
                if r.chunk.source not in sources:
                    sources.append(r.chunk.source)
        rank = _first_rank(sources, expected)
        if rank:
            hits += 1
            rr_sum += 1.0 / rank

    return EvalResult(
        hit_at_k=hits / grounded if grounded else 0.0,
        mrr=rr_sum / grounded if grounded else 0.0,
        refusal_accuracy=open_ok / open_total if open_total else 0.0,
        n_grounded=grounded,
        n_open=open_total,
    )
