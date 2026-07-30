# ZenaidaRAG — imagen de la API. Build verificado en CI (GitHub Actions).
# Nota: el modelo de embeddings (~470 MB) se descarga en el primer arranque y
# se cachea en /home/appuser/.cache (montar un volumen para persistirlo).
FROM python:3.12-slim

# Evita prompts y bytecode; salida sin buffer para ver logs en vivo.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Dependencias primero (mejor cache de capas).
COPY pyproject.toml README.md ./
COPY zenaidarag ./zenaidarag
RUN pip install --no-cache-dir .

# 2) Documentos de ejemplo (los datos reales van montados, nunca en la imagen).
COPY sample_docs ./sample_docs

# 3) Usuario no-root por seguridad.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Chequeo de salud contra el endpoint /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# Arranca la API. Para usar la CLI: docker run ... zenaidarag ingest sample_docs
ENTRYPOINT ["zenaidarag"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
