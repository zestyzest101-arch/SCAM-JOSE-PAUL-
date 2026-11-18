# SCAM JOSE PAUL 3D — FastAPI API + Three.js client.
# Alpine keeps the runtime small and patched; the app runs as a non-root user.
FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=3000

# Refresh the OS packages in the image before installing anything.
RUN echo "os-refresh 2026-11-18" && apk upgrade --no-cache

WORKDIR /app

COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

# Application code. The JSON save file and the SQLite mirror are created at
# runtime inside /app/data, which is owned by the runtime user below.
COPY game_core.py ./
COPY backend ./backend
COPY db ./db
COPY web ./web
COPY assets ./assets

RUN adduser -D -u 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 3000

CMD ["sh", "-c", "exec uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-3000}"]
