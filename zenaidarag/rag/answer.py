"""Orquestacion del RAG: recuperar -> (hibrido/rerank) -> prompt -> responder.

Flujo (Fase 4):
1. Recupera `fetch_k` candidatos semanticos (scores coseno).
2. **Negativa honesta** basada en el score SEMANTICO (coseno) contra `min_score`
   (ADR-006). Se decide ANTES de reordenar, para no romper la calibracion del
   umbral: rerank/hibrido cambian la escala del score pero no deben afectar la
   decision de "hay o no contexto".
3. Si hay contexto: opcionalmente fusiona con BM25 (hibrido) y/o reordena con
   cross-encoder (rerank), y toma los mejores `top_k` para el prompt.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from zenaidarag.rag.hybrid import bm25_rank, rrf_fuse
from zenaidarag.rag.prompt import REFUSAL, build_prompt
from zenaidarag.rag.retrieve import filter_by_score, retrieve
from zenaidarag.store import Retrieved


@dataclass
class Answer:
    """Resultado de una consulta RAG."""

    text: str
    sources: list[str] = field(default_factory=list)
    retrieved: list[Retrieved] = field(default_factory=list)
    refused: bool = False


def _sources(chunks: list[Retrieved]) -> list[str]:
    seen: list[str] = []
    for r in chunks:
        if r.chunk.source not in seen:
            seen.append(r.chunk.source)
    return seen


def select_context(
    question: str,
    store,
    embeddings,
    top_k: int = 4,
    min_score: float = 0.35,
    fetch_k: int = 12,
    use_hybrid: bool = False,
    reranker=None,
) -> list[Retrieved] | None:
    """Devuelve los fragmentos para el prompt, o None si no hay contexto util.

    La decision de negativa usa el score semantico (coseno). El reordenamiento
    (hibrido/rerank) solo afecta *que* top_k fragmentos se citan.
    """
    candidates = retrieve(question, store, embeddings, max(fetch_k, top_k))
    passed = filter_by_score(candidates, min_score)
    if not passed:
        return None  # negativa honesta

    context = candidates
    if use_hybrid:
        all_chunks = store.get_all() if hasattr(store, "get_all") else [
            r.chunk for r in candidates
        ]
        bm25 = bm25_rank(question, all_chunks, max(fetch_k, top_k))
        context = rrf_fuse([candidates, bm25], top_n=max(fetch_k, top_k))

    if reranker is not None:
        return reranker.rerank(question, context, top_k)
    return context[:top_k]


def answer(
    question: str,
    store,
    embeddings,
    llm,
    top_k: int = 4,
    min_score: float = 0.35,
    fetch_k: int = 12,
    use_hybrid: bool = False,
    reranker=None,
) -> Answer:
    """Responde una pregunta con RAG. Negativa honesta si no hay contexto util."""
    chunks = select_context(
        question, store, embeddings, top_k, min_score, fetch_k, use_hybrid, reranker
    )
    if not chunks:
        return Answer(text=REFUSAL, sources=[], retrieved=[], refused=True)

    prompt = build_prompt(question, chunks)
    text = llm.generate(prompt)
    return Answer(text=text, sources=_sources(chunks), retrieved=chunks, refused=False)


def answer_stream(
    question: str,
    store,
    embeddings,
    llm,
    top_k: int = 4,
    min_score: float = 0.35,
    fetch_k: int = 12,
    use_hybrid: bool = False,
    reranker=None,
) -> tuple[Iterator[str], list[str]]:
    """Version streaming: devuelve (iterador de tokens, fuentes). Para SSE."""
    chunks = select_context(
        question, store, embeddings, top_k, min_score, fetch_k, use_hybrid, reranker
    )
    if not chunks:
        return iter([REFUSAL]), []
    prompt = build_prompt(question, chunks)
    return llm.stream(prompt), _sources(chunks)
