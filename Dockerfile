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
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /data

# Hesap havuzu DB'si volume olarak disari alinir (token'lar image'da kalmaz)
VOLUME ["/data"]

EXPOSE 7001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7001/mcp',timeout=4).status in (200,405,406) else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
