# Imagen del backend: sirve tanto para la API como para el worker.
#
# El contexto de construcción es la RAÍZ del repositorio, no `backend/`, porque
# los datos de demostración viven en `fixtures/` y deben entrar en la imagen.
# Constrúyela así:
#   docker build -f backend/Dockerfile -t creator-signal-backend .
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FIXTURES_DIR=/fixtures \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# `curl` se usa en el healthcheck; `libpq5` lo necesita psycopg en modo binario.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libpq5 procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Las dependencias se instalan antes que el código para aprovechar la caché.
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app

# Los datos de demostración. `FIXTURES_DIR` (arriba) apunta aquí.
COPY fixtures /fixtures

# La aplicación no se ejecuta como root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /fixtures
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
