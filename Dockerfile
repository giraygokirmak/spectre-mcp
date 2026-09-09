FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TWS_HTTP_BACKEND=curl \
    TWS_TELEMETRY=0 \
    SPECTRE_DB=/data/accounts.db

WORKDIR /app

# Proje kaynagini image'a gom (kurulum kaynaktan, lock ile tekrarlanabilir)
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# HTTP entrypoint + seed scripti
COPY docker/http_server.py /app/http_server.py
COPY docker/entrypoint.sh /app/entrypoint.sh
COPY docker/healthcheck.py /app/healthcheck.py
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /data

# Hesap havuzu DB'si volume olarak disari alinir (token'lar image'da kalmaz)
VOLUME ["/data"]

# Port hardcode degil: healthcheck.py SPECTRE_HTTP_PORT env'ini runtime'da okur.
# .env'de port degisirse rebuild gerekmeksizin 'docker compose up -d' yeterli.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python /app/healthcheck.py

ENTRYPOINT ["/app/entrypoint.sh"]
