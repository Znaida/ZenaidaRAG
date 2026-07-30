# ZenaidaRAG — Guía del proyecto

Asistente RAG de **apoyo veterinario**: responde preguntas sobre un corpus de documentos con recuperación semántica, **citación de fuentes** y **negativa honesta** (no alucina). Python/FastAPI. **Indexación y recuperación 100% locales** (embeddings + ChromaDB); el LLM es intercambiable: Gemini/OpenAI (nube) por defecto u **Ollama** para generación 100% local. Publicable sin datos de terceros. Reescritura limpia y propia de un motor RAG que ya construí antes.

## Antes de programar
- **Lee `docs/ROADMAP.md`** (visión, alcance, stack, ADRs, fases) y `docs/adr/`.
- Trabajá **fase por fase** (0 → 6). No avanzar con algo roto.

## Reglas
- **Nunca commitear:** `.env`, API keys, el índice vectorial, `data/docs/` reales, ni **PDFs con copyright** (los libros de veterinaria se usan solo en local para demo/video). El repo ships con `sample_docs/` de licencia abierta.
- **Tests desde la Fase 1** (pytest). Cobertura del núcleo ≥70%.
- **Runnable por cualquiera:** `git clone` → `pip install` → 1 API key → `ingest` sample_docs → `ask`. Nada de nube obligatoria (ChromaDB + embeddings locales por defecto).
- **Git:** el usuario hace commits/push manualmente. No hacer push.
- Toda decisión de arquitectura nueva → ADR en `docs/adr/`.

## Stack
Python 3.12 · FastAPI (SSE) · Typer (CLI) · **ChromaDB** local (Azure AI Search opcional) · **sentence-transformers** local ($0) · LLM provider-agnóstico (Gemini por defecto; OpenAI/Ollama-local/`fake` opc.) · pypdf/python-docx/pandas · pytest · Docker · GitHub Actions.

## Diseño clave
Interfaces para intercambiar piezas: `Embeddings`, `VectorStore`, `LLMProvider`. Prompt obliga a **citar fuentes** y a decir "no tengo información suficiente" cuando el contexto no cubre la pregunta (anti-alucinación — crítico en dominio veterinario).

## Estado actual
**Fases 0–7 completas — todo probado en local. Publicado en GitHub por el usuario.**
- Fase 0: esqueleto, CLI, CI, tests de humo.
- Fase 1: loaders multi-formato, chunking, embeddings locales, ChromaStore, `ingest`.
- Fase 2: recuperación top-k, prompt con citación + negativa honesta, proveedores LLM (Gemini default `gemini-3.5-flash-lite`, OpenAI opc., **Ollama** local opc. `llm/ollama.py` vía httpx, `fake` para tests), `ask`.
- Fase 3: `api.py` con `GET /health` y `POST /ask` (SSE: `token`/`sources`/`done`), CORS, engine inyectable; comando `serve`.
- Fase 4 (opcional): búsqueda híbrida (BM25+RRF en `rag/hybrid.py`), reranking cross-encoder (`rag/rerank.py`, multilingüe, ~450 MB), set de evaluación (`eval/questions.json` + `evaluate.py` + comando `eval`: hit@k/MRR/negativa, sin LLM). Flags `USE_HYBRID`/`USE_RERANK` off por defecto. Decisión clave: la negativa honesta usa el score SEMÁNTICO (coseno) antes de reordenar. Sobre sample_docs el baseline ya da 100%/1.000 (corpus chico); mejoras pagan en corpus grandes. Verificado con cross-encoder real; modelo borrado luego para liberar disco (ADR-011).
- Fase 5 (opcional): bot de Telegram por polling (`channels/telegram.py`, cliente httpx fino) + adaptador Teams/Bot Framework documentado (`channels/teams_adapter.py`, webhook). Ambos reutilizan el motor RAG vía `channels.format_reply`. Lógica unit-testeada con HTTP mockeado (sin red). Comando `telegram`. Token en `TELEGRAM_BOT_TOKEN`.
- Fase 6: Dockerfile (no-root, healthcheck) + docker-compose + .dockerignore; CI con matriz py3.10/3.12, gate cobertura 70%, build de Docker; diagrama mermaid en README; auditoría de seguridad OK (key solo en `.env`, índice ignorado).
- **66 tests**, ~80% cobertura del núcleo. Embeddings multilingüe, `min_score=0.35`. Docker **no** verificado en local (sin Docker); se construye en CI. Telegram/Teams no verificados en vivo (sin bot token / sin Azure); lógica unit-testeada.
- Nota entorno: puerto 8000 puede estar ocupado por otra app local ("zenAIda"); usar `API_PORT`.
- **Solo falta para publicar (lo hace el usuario): `git init` + commit + push, y grabar video demo.**
