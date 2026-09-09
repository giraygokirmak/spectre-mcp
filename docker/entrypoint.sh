#!/bin/sh
set -e

# .env'den gelen hesap bilgileriyle pool'u seed et (idempotent):
# hesap zaten DB'de ise tekrar ekleme yapilmaz.
if [ -n "$SPECTRE_USERNAME" ] && [ -n "$SPECTRE_AUTH_TOKEN" ] && [ -n "$SPECTRE_CT0" ]; then
  if ! spectre list 2>/dev/null | grep -q "@${SPECTRE_USERNAME}"; then
    echo "[entrypoint] Pool seed: @${SPECTRE_USERNAME} hesabi ekleniyor"
    spectre add "$SPECTRE_USERNAME" "auth_token=${SPECTRE_AUTH_TOKEN}; ct0=${SPECTRE_CT0}" || true
  else
    echo "[entrypoint] @${SPECTRE_USERNAME} zaten pool'da"
  fi
else
  echo "[entrypoint] UYARI: SPECTRE_USERNAME/AUTH_TOKEN/CT0 eksik; server hesapsiz basliyor"
fi

exec python /app/http_server.py
