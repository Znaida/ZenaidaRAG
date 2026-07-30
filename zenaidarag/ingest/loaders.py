"""Extractores de texto por formato, tras una interfaz comun (ADR-007).

Cada loader recibe una ruta y devuelve el texto plano del documento. El
formato se resuelve por la extension del archivo. Formatos soportados en v1:
PDF, DOCX, MD, TXT, CSV, XLSX.
"""
from __future__ import annotations

from pathlib import Path

# Extensiones soportadas (en minuscula, con punto).
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".csv", ".xlsx"}


class UnsupportedFormatError(ValueError):
    """La extension del archivo no tiene un loader asociado."""


def _load_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(parts)


def _load_docx(path: Path) -> str:
    import docx  # python-docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def _load_csv(path: Path) -> str:
    import pandas as pd

    df = pd.read_csv(path)
    return df.to_csv(index=False)


def _load_xlsx(path: Path) -> str:
    import pandas as pd

    sheets = pd.read_excel(path, sheet_name=None)
    parts = []
    for name, df in sheets.items():
        parts.append(f"# Hoja: {name}")
        parts.append(df.to_csv(index=False))
    return "\n".join(parts)


_LOADERS = {
    ".txt": _load_txt,
    ".md": _load_txt,
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".csv": _load_csv,
    ".xlsx": _load_xlsx,
}


def is_supported(path: Path) -> bool:
    """True si existe un loader para la extension del archivo."""
    return path.suffix.lower() in _LOADERS


def load_document(path: str | Path) -> str:
    """Extrae el texto plano de un documento segun su extension.

    Lanza UnsupportedFormatError si el formato no esta soportado y
    FileNotFoundError si la ruta no existe.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    loader = _LOADERS.get(path.suffix.lower())
    if loader is None:
        raise UnsupportedFormatError(path.suffix)
    return loader(path)
