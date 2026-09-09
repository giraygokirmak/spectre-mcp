# spectre-mcp - healthcheck script
# Port'u SPECTRE_HTTP_PORT env'inden runtime'da okur; Dockerfile HEALTHCHECK bunu cagirir.
# Boylece .env'de port degistiginde rebuild gerekmeksizin dogru porta bakar.
import os
import sys
import urllib.request
import urllib.error

PORT = os.environ.get("SPECTRE_HTTP_PORT", "7001")
BASE = f"http://127.0.0.1:{PORT}/mcp"

# Amac: "sunucu ayakta ve TCP/HTTP seviyesinde cevap veriyor mu?"
# Session/header eksikliginden 4xx donmesi normaldir; 4xx de sunucunun
# SAGLIKLI oldugunun kanitidir. 307, FastMCP mount'unun slash redirect'idir
# (server calisiyor olmasaydi TCP seviyesinde hic cevap gelmezdi).
# Sadece 5xx / baglanti hatasi fail'dir.
OK_CODES = {200, 301, 302, 303, 307, 308, 400, 401, 404, 405, 406, 409}


def probe(url: str):
    """Tek POST dene; (http_kodu, location_header) dondur. Baglanti hatasi firlatir."""
    req = urllib.request.Request(
        url,
        method="POST",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=4)
        return resp.status, resp.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")


try:
    code, location = probe(BASE)
    # urllib 307'de POST body'sini tekrar gonderemez ve HTTPError firlatir;
    # bu yuzden redirect'i 1 kez elle izliyoruz (final kod gercek saglik sinyali).
    if code in (301, 302, 303, 307, 308) and location:
        location = location.replace("0.0.0.0", "127.0.0.1")
        code, _ = probe(location)
except Exception as e:
    print(f"[healthcheck] baglanti hatasi ({BASE}): {e}", file=sys.stderr)
    sys.exit(1)

if code in OK_CODES:
    sys.exit(0)

print(f"[healthcheck] beklenmeyen HTTP {code} ({BASE})", file=sys.stderr)
sys.exit(1)