#!/bin/sh
# Entrypoint container backend.
#   MIGRATE_ON_START=false  -> lewati `alembic upgrade head` (default: true)
#   PORT                    -> port server (default 8000)
#   UVICORN_ARGS            -> argumen tambahan uvicorn, mis. "--proxy-headers --forwarded-allow-ips=10.0.0.1"
set -e

if [ "${MIGRATE_ON_START:-true}" = "true" ]; then
    echo "[entrypoint] alembic upgrade head"
    alembic upgrade head
fi

echo "[entrypoint] menjalankan uvicorn di port ${PORT:-8000}"
# shellcheck disable=SC2086
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" ${UVICORN_ARGS:-}
