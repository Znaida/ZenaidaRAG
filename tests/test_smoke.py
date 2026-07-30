"""Tests de humo de la Fase 0: el paquete importa, la CLI responde, la config carga."""
from __future__ import annotations

from typer.testing import CliRunner

from zenaidarag import __version__
from zenaidarag.cli import app
from zenaidarag.config import get_settings

runner = CliRunner()


def test_version_matches_package():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_core_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "ask" in result.stdout


def test_settings_defaults_reflect_adrs():
    s = get_settings()
    assert s.embeddings_provider == "local"  # ADR-004
    assert s.vector_store == "chroma"  # ADR-003
    assert s.llm_provider == "gemini"  # ADR-005 (default; provider-agnostico)
    assert s.top_k > 0
