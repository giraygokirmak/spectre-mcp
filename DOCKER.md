# spectre-mcp — Standalone Docker Paketi

`projects/spectre-mcp` altındaki bu repo, `Dockerfile` + `docker-compose.yml` ile tek başına bir container olarak çalışır. MCP endpoint'i Docker host üzerinden `http://<host>:7001/mcp` adresinde (streamable-http transport) yayınlanır.

## Dosyalar

- `Dockerfile` — python:3.12-slim tabanlı; projeyi `pip install .` ile kurar, `/data` volume'ünde `SPECTRE_DB` (twscrape hesap havuzu) tutar, port 7001 expose eder, healthcheck `/mcp` üzerinden.
- `docker-compose.yml` — `spectre-mcp` servisi; `.env` okur, `7001:7001` port eşlemesi, `spectre-data` named volume.
- `.env.example` — kopyalayıp `.env` yapılır: `SPECTRE_USERNAME` + `SPECTRE_AUTH_TOKEN` + `SPECTRE_CT0` (x.com DevTools → Application → Cookies). `.env` `.gitignore` ve `.dockerignore`'da; image'a/token'lar repoya girmez.
- `docker/entrypoint.sh` — env'deki üç değer doluysa `spectre add` ile hesabı pool'a idempotent seed eder (zaten varsa atlar), sonra HTTP sunucusunu başlatır.
- `docker/http_server.py` — FastMCP'yi `transport="streamable-http"`, `host=0.0.0.0`, `port=7001`, `path="/mcp"`, `host_origin_protection=False` ile çalıştırır. Koruma kapalı çünkü LAN'den (192.168.2.x) erişimde FastMCP 421 döndürüyor.

## Kurulum

```sh
cd projects/spectre-mcp
cp .env.example .env
# .env icine auth_token ve ct0 degerlerini yaz
docker compose build
docker compose up -d
```

## Dogrulama

```sh
curl -X POST http://localhost:7001/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
docker exec spectre-mcp spectre list   # hesap pool'da mi
```

## Notlar

- Cookie'ler suresiz degildir; X oturumu duserse `.env`'deki degerleri yenileyip `docker compose restart` yeterli (DB volume'da kaldigi icin pool guncellenir).
- Container ici DB yolu: `/data/accounts.db` (`SPECTRE_DB` env ile degistirilebilir).
- `SPECTRE_PROXY` setlenirse tum istekler o proxy'den cikar.
- Coklu hesap: pool'a ek hesap `docker exec spectre-mcp spectre add <kullanici> "auth_token=...; ct0=..."` ile eklenir.
- OpenClaw tarafinda native kayit: `openclaw mcp add spectre-docker --url http://<host>:7001/mcp --transport streamable-http` seklinde.
