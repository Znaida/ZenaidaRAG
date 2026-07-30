"""Tests del prompt anti-alucinacion (ADR-006)."""
from __future__ import annotations

from zenaidarag.rag.prompt import REFUSAL, build_prompt, format_context
from zenaidarag.store import Chunk, Retrieved


def _r(text, source, score=0.9):
    return Retrieved(chunk=Chunk(id=source, text=text, source=source), score=score)


def test_prompt_includes_context_and_question():
    chunks = [_r("Cepillar los dientes del perro a diario.", "dental.md")]
    prompt = build_prompt("Cada cuanto cepillo a mi perro?", chunks)
    assert "dental.md" in prompt
    assert "Cepillar los dientes" in prompt
    assert "Cada cuanto cepillo" in prompt


def test_prompt_states_refusal_rule():
    prompt = build_prompt("x", [_r("y", "z")])
    assert REFUSAL in prompt  # la regla de negativa honesta esta presente


def test_prompt_tells_model_not_to_add_sources_line():
    # Las fuentes las agrega la app, no el LLM (evita duplicados).
    prompt = build_prompt("x", [_r("y", "z")])
    assert 'NO agregues una linea de "Fuentes:"' in prompt


def test_prompt_without_context_marks_empty():
    prompt = build_prompt("pregunta sin corpus", [])
    assert "(sin fragmentos relevantes)" in prompt


def test_format_context_numbers_fragments():
    ctx = format_context([_r("a", "s1"), _r("b", "s2")])
    assert "Fragmento 1" in ctx and "Fragmento 2" in ctx
    assert "s1" in ctx and "s2" in ctx
