# Architecture Decision Records — ZenaidaRAG

Los ADR completos (Contexto · Decisión · Consecuencias) están en `docs/ROADMAP.md`, sección 4. Índice:

| ADR | Decisión |
|-----|----------|
| ADR-001 | Producto propio, sin datos ni dependencias de proyectos previos |
| ADR-002 | Backend en Python + FastAPI (CLI con Typer) |
| ADR-003 | Vector store: ChromaDB local por defecto (Azure AI Search opcional) |
| ADR-004 | Embeddings locales por defecto (sentence-transformers, $0) |
| ADR-005 | LLM provider-agnóstico (OpenAI por defecto) |
| ADR-006 | Calidad RAG: chunking + citación + negativa honesta (anti-alucinación) |
| ADR-007 | Ingesta multi-formato (PDF/DOCX/MD/TXT/CSV/XLSX) |
| ADR-008 | Interfaces: CLI + API; canales Telegram/Teams opcionales |
| ADR-009 | Datos de ejemplo abiertos; libros con copyright solo local |
| ADR-010 | Puertas de calidad: tests, Docker, CI |
| ADR-011 | Calidad de recuperación: híbrido (BM25+RRF) + reranking + set de evaluación (opcionales) |
