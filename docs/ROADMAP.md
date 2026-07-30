# ZenaidaRAG — Ruta de Desarrollo

> **Asistente RAG de apoyo veterinario.** Un chatbot que responde preguntas sobre un corpus de documentos veterinarios, con **citación de fuentes** y **cero alucinación** (solo responde con base en los documentos). 100% propio, corre local, publicable sin datos de terceros.

**Estado:** Planeación (Fase 0)
**Autor:** Rudbel F. Ordaz — github.com/Znaida
**Marca:** ZenaidaRAG
**Última actualización:** 2026-07-28

---

## 0. Cómo usar este documento

Plan maestro para una conversación de desarrollo dedicada. Al abrir la conversación nueva:

> "Voy a desarrollar ZenaidaRAG. Lee `docs/ROADMAP.md` y `docs/adr/`. Empecemos por la Fase 0."

Ejecutar **fase por fase**; cada una deja algo que funciona.

### Origen (honesto)
Es la **reescritura limpia y propia** de un motor RAG que ya construí antes (versiones previas con ChromaDB/Azure AI Search + Bot Framework/Telegram). Aquí se rehace **desde cero, ordenado, con mi marca y datos propios/de ejemplo** — sin ninguna dependencia ni dato de proyectos anteriores. El código es mío; los datos son de ejemplo o míos.

---

## 1. Visión del producto

**ZenaidaRAG** es un asistente que:
- **Ingiere** documentos veterinarios (PDF/DOCX/MD/TXT/CSV) a un índice vectorial.
- **Responde** preguntas recuperando los fragmentos relevantes (búsqueda semántica) y generando la respuesta con un LLM.
- **Cita las fuentes** de cada respuesta y **se niega a responder** si no hay base documental (anti-alucinación).
- Corre **100% local** (embeddings locales + ChromaDB), con opción de backends en la nube.

### Principio rector: "clona y corre en 2 minutos"
El mayor valor de portafolio es que **cualquier reclutador pueda correrlo**: `git clone` → `pip install` → 1 API key → `ingest` los docs de ejemplo → `ask`. Nada de cuentas de Azure obligatorias.

---

## 2. Alcance

### Dentro (v1.0)
- Ingesta multi-formato (PDF/DOCX/MD/TXT/CSV) → chunking con solapamiento → embeddings → ChromaDB.
- Recuperación top-k + generación con LLM + **citación de fuentes**.
- **Negativa honesta** cuando no hay contexto suficiente.
- Embeddings **locales** por defecto (sentence-transformers, $0); LLM configurable (OpenAI por defecto).
- Interfaces: **CLI** (`ingest`, `ask`) + **API FastAPI** (`/ask` con streaming SSE).
- `sample_docs/` con documentos veterinarios de **licencia abierta** (no libros con copyright).
- Tests (pytest), Dockerfile, `.env.example`, README + video demo.

### Opcional / Fuera (v1.0)
- **Reranking** + búsqueda híbrida (mejora de calidad) — opcional en Fase 4.
- **Canal Telegram** + adaptador **Teams/Bot Framework** (documentado) — Fase 5, opcional.
- **Backend Azure AI Search** como alternativa enchufable a ChromaDB — documentado, no obligatorio.
- UI web elaborada, multi-usuario/auth, fine-tuning — futuro.

### ⚠️ Regla de datos y copyright
- Los **libros de veterinaria con copyright** se usan SOLO en local (demo/video), **nunca se commitean**.
- El repo público ships con **documentos de licencia abierta / open-access** (o placeholders) + instrucción "agregá tus propios PDFs en `data/docs/`".
- `.gitignore` excluye `data/docs/` reales, `.env`, el índice vectorial y cualquier PDF con copyright.

---

## 3. Stack técnico

| Capa | Tecnología | Por qué |
|---|---|---|
| Lenguaje/API | **Python 3.12 + FastAPI** | Consistente con mi perfil; ecosistema RAG nativo |
| Vector store | **ChromaDB** (local) por defecto · Azure AI Search opcional | Corre sin nube; muestro que sé el backend gestionado |
| Embeddings | **sentence-transformers** local ($0) · nube opcional | Gratis, offline, reproducible |
| LLM | **OpenAI** por defecto · Groq/Gemini/Ollama opcionales (interfaz) | 1 sola key para arrancar; provider-agnóstico |
| Ingesta | `pypdf`, `python-docx`, `pandas`, `openpyxl` | Multi-formato |
| Calidad RAG | chunking con solapamiento, citación, (opc.) reranking + híbrido | Precisión 2026 |
| Interfaces | CLI (Typer) + FastAPI (SSE) · Telegram/Teams opcional | Runnable + demostrable |
| Calidad | **pytest, Docker, GitHub Actions, .env.example** | Señal verificable para el reclutador |

---

## 4. Architecture Decision Records (ADR)

### ADR-001 — Producto propio, sin datos ni dependencias de proyectos previos
- **Contexto:** Tengo versiones previas del motor con datos de un cliente (confidenciales) y de una tesis (de un tercero).
- **Decisión:** Reescritura limpia desde cero, con mi marca (ZenaidaRAG) y datos de ejemplo propios/abiertos. Ninguna línea ni documento de los proyectos previos.
- **Consecuencias:** (+) 100% publicable, sin confidencialidad comprometida. (+) Historia de CV limpia. (−) Rehacer (mitigado: ya domino el patrón).

### ADR-002 — Backend en Python + FastAPI
- **Decisión:** Python 3.12 + FastAPI para la API; CLI con Typer.
- **Consecuencias:** (+) Coherente con mi CV; SDKs de IA de primera clase. (−) Ninguna relevante.

### ADR-003 — Vector store: ChromaDB local por defecto (Azure AI Search opcional)
- **Contexto:** El "corre en 2 minutos" es clave para el portafolio; Azure AI Search exige cuenta de nube.
- **Decisión:** ChromaDB persistente local por defecto. Azure AI Search como **backend enchufable opcional** (interfaz `VectorStore`), documentado pero no requerido para correr.
- **Consecuencias:** (+) Cualquiera lo corre sin nube. (+) Muestro que sé el backend gestionado. (−) Mantener 2 implementaciones tras una interfaz (aceptable; la de Azure es opcional).

### ADR-004 — Embeddings locales por defecto
- **Decisión:** `sentence-transformers` local, costo $0. Embeddings de nube (OpenAI/Gemini) opcionales por config.
- **Nota 2026-07-28 (Fase 2):** el modelo por defecto pasa de `all-MiniLM-L6-v2` (inglés) a **`paraphrase-multilingual-MiniLM-L12-v2`** (multilingüe). Medido sobre `sample_docs/` en español: con el modelo inglés los scores se comprimen (relevante ~0.48 vs irrelevante ~0.30, y a veces el doc correcto no queda #1); con el multilingüe la separación es amplia (relevante ~0.75 vs irrelevante ~0.13) y el ranking es correcto. Justifica el umbral `min_score=0.35` para la negativa honesta. Costo: descarga ~470 MB (vs ~90 MB); aceptable para el principio "corre en 2 minutos".
- **Consecuencias:** (+) Offline, gratis, reproducible, buena calidad en español. (−) Modelo más pesado; algo menos preciso que embeddings de nube (se compensa con reranking en Fase 4).

### ADR-005 — LLM provider-agnóstico
- **Decisión:** Interfaz `LLMProvider`; adaptadores para Gemini, OpenAI y un `fake` (tests/offline). Solo 1 key para arrancar.
- **Nota 2026-07-28 (Fase 2):** el proveedor por defecto pasa a **Gemini** (`gemini-3.5-flash-lite`, free tier 500 req/día — viable para demo y CV) por disponibilidad de key; OpenAI queda como alternativa. El `fake` permite correr el RAG end-to-end sin red.
- **Consecuencias:** (+) Flexible y testeable con un proveedor falso. (−) Normalizar diferencias entre APIs.

### ADR-006 — Calidad del RAG (chunking, citación, negativa honesta)
- **Decisión:** Chunking con solapamiento + metadatos de fuente; el prompt obliga a **citar** y a **responder "no tengo información suficiente"** si el contexto no cubre la pregunta. (Reranking + híbrido = mejora opcional Fase 4.)
- **Consecuencias:** (+) Anti-alucinación, confiable (crítico en dominio veterinario). (−) Ajuste fino de tamaños de chunk (iterativo).

### ADR-007 — Ingesta multi-formato
- **Decisión:** Soportar PDF/DOCX/MD/TXT/CSV/XLSX con extractores por formato tras una interfaz común.
- **Consecuencias:** (+) Cubre la mayoría de material veterinario. (−) Manejo de PDFs mal escaneados (fuera de v1; se documenta).

### ADR-008 — Interfaces: CLI + API (canales opcionales)
- **Decisión:** CLI (`ingest`/`ask`) y API FastAPI (SSE) en v1. Telegram y Teams/Bot Framework como **adaptadores opcionales** (Fase 5), documentados pero no requeridos.
- **Consecuencias:** (+) Runnable y demostrable ya; los canales suman sin bloquear. (−) Ninguna.

### ADR-009 — Datos de ejemplo abiertos + copyright
- **Decisión:** El repo ships con documentos veterinarios de **licencia abierta / open-access** (o placeholders). Los libros con copyright se usan solo local (demo/video) y van en `.gitignore`.
- **Consecuencias:** (+) Repo limpio legalmente. (−) La demo pública usa menos material (el video muestra el potencial completo).

### ADR-010 — Puertas de calidad
- **Decisión:** pytest (núcleo: ingesta, recuperación, prompt) ≥70%; Docker; GitHub Actions (lint+tests); `.env.example`; README con GIF/video.
- **Consecuencias:** (+) Verificable y profesional. (−) Disciplina de tests desde el inicio.

### ADR-011 — Calidad de recuperación: híbrido + reranking (Fase 4)
- **Contexto:** El bi-encoder (embeddings) es rápido pero aproximado; en corpus grandes/ruidosos puede rankear mal. Se busca subir precisión sin romper el flujo base.
- **Decisión:** Añadir dos mejoras **opcionales por config** (`USE_HYBRID`, `USE_RERANK`, off por defecto): (1) **búsqueda híbrida** = BM25 (keyword) fusionado con la semántica vía **Reciprocal Rank Fusion**; (2) **reranking** con cross-encoder multilingüe sobre los `fetch_k` candidatos. Se agrega un **set de evaluación** (`eval/questions.json`) y el comando `zenaidarag eval` (hit@k, MRR, precisión de negativa) — **sin usar el LLM**, no consume cuota.
- **Decisión clave (anti-alucinación):** la **negativa honesta se decide con el score SEMÁNTICO (coseno)** contra `min_score`, ANTES de reordenar. Rerank/híbrido cambian la escala del score y solo afectan *qué* top_k se citan, nunca la decisión de "hay o no contexto".
- **Nota 2026-07-29:** sobre `sample_docs/` (3 docs, 7 chunks) el baseline ya da **hit@k=100%, MRR=1.000**: el corpus es demasiado pequeño para mostrar delta. Las mejoras pagan en corpus grandes (p.ej. los libros reales en local). Por eso quedan **off por defecto** (respetan "corre en 2 minutos" y $0) y se activan por config.
- **Consecuencias:** (+) Precisión 2026 disponible y medible; anti-alucinación intacta. (−) El reranker añade descarga de modelo (~450 MB) y latencia; por eso es opcional.

---

## 5. Fases de desarrollo

### Fase 0 — Cimientos (½ día)
- **Objetivo:** Repo y esqueleto listos.
- **Tareas:** estructura de carpetas; `pyproject`/`requirements`; `.gitignore` (`.env`, `data/docs/`, índice, `*.pdf` reales); `.env.example`; `sample_docs/` con 2–3 docs abiertos; esqueleto CLI (`--help`); CI esqueleto en verde; ADRs; CLAUDE.md; README borrador.
- **Salida:** repo booteable, CI verde.

### Fase 1 — Ingesta (1–2 días)
- **Objetivo:** Convertir documentos en índice vectorial.
- **Tareas:** extractores por formato (PDF/DOCX/MD/TXT/CSV) tras interfaz común; chunking con solapamiento + metadatos de fuente; interfaz `Embeddings` (local por defecto, ADR-004); interfaz `VectorStore` + impl ChromaDB (ADR-003); comando `zenaidarag ingest <carpeta>`.
- **Entregable:** `ingest sample_docs/` crea el índice; se ve cuántos chunks entraron.
- **Salida:** pipeline de ingesta + tests (con docs de ejemplo).

### Fase 2 — Recuperación + respuesta (walking skeleton) (1–2 días)
- **Objetivo:** Preguntar y obtener respuesta fundamentada.
- **Tareas:** recuperación top-k; interfaz `LLMProvider` + OpenAI (ADR-005); prompt con contexto + **citación** + **negativa honesta** (ADR-006); comando `zenaidarag ask "..."` que imprime respuesta + fuentes.
- **Entregable:** "¿Cuál es la dosis de X en perros?" → responde citando el documento fuente (o dice que no tiene info).
- **Salida:** RAG end-to-end por CLI + tests del prompt/recuperación.

### Fase 3 — API + streaming (1 día)
- **Objetivo:** Exponer el RAG como servicio.
- **Tareas:** FastAPI `POST /ask` con **streaming SSE**; `GET /health`; (opcional) UI web mínima o página estática de prueba; CORS.
- **Entregable:** pregunto por HTTP y recibo la respuesta token-a-token con fuentes.
- **Salida:** API funcional + tests de endpoint.

### Fase 4 — Calidad de recuperación (opcional, 1–2 días)
- **Objetivo:** Subir la precisión.
- **Tareas:** **reranking** (cross-encoder local) de los top-k; **búsqueda híbrida** (semántica + keyword); ajuste de chunking; mini set de evaluación (preguntas→fuente esperada).
- **Entregable:** mejores respuestas medibles en el set de evaluación.
- **Salida:** calidad 2026 + métricas en el README.

### Fase 5 — Canales (opcional, 1–2 días)
- **Objetivo:** Demostrar integración multi-canal.
- **Tareas:** bot de **Telegram** (polling) sobre la misma API; **adaptador Teams/Bot Framework** documentado (webhook), sin requerir despliegue.
- **Entregable:** pregunto desde Telegram y responde.
- **Salida:** canal extra + documentación de Teams-ready.

### Fase 6 — Pulido y publicación (1–2 días)
- **Objetivo:** Repo de portafolio impecable.
- **Tareas:** subir cobertura; Dockerfile + compose; CI completo; **README** (qué/por qué/arquitectura/GIF/cómo correr/nota de copyright/créditos); diagrama; **grabar video demo** (con los libros reales en local); auditoría de seguridad (sin keys, sin PDFs con copyright).
- **Salida:** **v1.0 pública.** Lista para el CV.

---

## 6. Estructura de carpetas propuesta

```
ZenaidaRAG/
├── zenaidarag/
│   ├── ingest/          # extractores por formato + chunking
│   ├── embeddings/      # interfaz + local (sentence-transformers) + nube opc.
│   ├── store/           # interfaz VectorStore + chroma.py (+ azure_search.py opc.)
│   ├── llm/             # interfaz LLMProvider + openai.py (+ groq/gemini/ollama opc.)
│   ├── rag/             # retrieve.py, prompt.py (citación + negativa), answer.py
│   ├── cli.py           # Typer: ingest, ask
│   └── api.py           # FastAPI: /ask (SSE), /health
├── channels/            # opcional: telegram.py, teams_adapter.py
├── sample_docs/         # documentos veterinarios de licencia abierta
├── data/                # gitignored: docs reales, índice chroma
├── tests/
├── docs/ (ROADMAP.md, adr/)
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt / pyproject.toml
├── LICENSE (MIT — Rudbel Ordaz)
├── CLAUDE.md
└── README.md
```

---

## 7. Metodología
- Fase por fase, demo funcional al cierre de cada una.
- Tests desde la Fase 1.
- **Seguridad/copyright:** nunca commitear `.env`, índices, ni PDFs con copyright.
- Commits atómicos; el usuario hace push (no automatizar).

---

## 8. Estimación

| Fase | Días |
|---|---|
| 0. Cimientos | 0.5 |
| 1. Ingesta | 1–2 |
| 2. Recuperación + respuesta | 1–2 |
| 3. API + streaming | 1 |
| 4. Calidad (opc.) | 1–2 |
| 5. Canales (opc.) | 1–2 |
| 6. Pulido + publicación | 1–2 |
| **Núcleo (0–3, 6)** | **~5–7 días** |
| **Con opcionales** | **~8–11 días** |

*El núcleo (fases 0–3 + 6) ya es un repo publicable fuerte; las fases 4–5 lo elevan.*

---

## 9. Framing para el CV (cuando esté listo)

**ZenaidaRAG — Asistente RAG de apoyo veterinario (Python)**

> Diseñé y construí un asistente de preguntas y respuestas sobre documentos, con recuperación semántica (ChromaDB + embeddings locales), citación de fuentes y negativa honesta ante falta de contexto. LLM configurable, ingesta multi-formato, API FastAPI con streaming, canales Telegram/Teams. Con tests, Docker y CI. Corre 100% local.

**Prueba:** repo público + video demo. Reemplaza los dos bullets de RAG previos por este (mismo motor, ahora propio y verificable).

---

## 10. Créditos y licencia
- Código propio bajo **MIT** (Rudbel F. Ordaz).
- Librerías: FastAPI, ChromaDB, sentence-transformers, OpenAI SDK, pypdf, python-docx, Typer.
- Documentos de ejemplo: de licencia abierta / open-access (citados en `sample_docs/README`).
