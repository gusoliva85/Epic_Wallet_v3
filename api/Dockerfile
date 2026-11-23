# ============================================================
#  Imagen de la API.
#
#  El contexto de build es la RAÍZ del repositorio, no api/:
#  hacen falta requirements.txt y migrations/, que viven afuera.
#
#  Referencia: 02_Documento_Tecnico.md §16
# ============================================================
FROM python:3.12-slim

# - PYTHONDONTWRITEBYTECODE: no deja .pyc dentro de la imagen.
# - PYTHONUNBUFFERED: los logs salen en el momento, no cuando se
#   llena un buffer. Sin esto `docker compose logs` miente sobre
#   cuándo pasó cada cosa.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/api

WORKDIR /app

# psycopg viene con los binarios incluidos ([binary]), así que no hace
# falta compilar nada ni instalar libpq. curl es para el healthcheck.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Las dependencias primero y solas: mientras requirements.txt no
# cambie, Docker reusa esta capa y el build no vuelve a bajar nada.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Después el código, que cambia en cada despliegue.
COPY api/ ./api/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Sin esto el proceso corre como root dentro del contenedor.
RUN useradd --create-home --uid 10001 epic && chown -R epic:epic /app
USER epic

EXPOSE 8000

# Un solo worker a propósito: son pocos usuarios conocidos y uvicorn
# resuelve la concurrencia con asyncio. Un segundo worker duplicaría
# las conexiones a la base sin resolver nada.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
