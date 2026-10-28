#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install it with: sudo pacman -S python" >&2
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 or newer is required.")
PY

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if [[ ! -f .venv/.deps-installed ]]; then
  .venv/bin/python -m pip install -r requirements.txt
  touch .venv/.deps-installed
fi

if [[ ! -d frontend/node_modules ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required. Install it with: sudo pacman -S nodejs npm" >&2
    exit 1
  fi
  (cd frontend && npm install)
fi

read -r configured_host configured_port < <(
  .venv/bin/python -c 'from backend.app.core.config import get_settings; s = get_settings(); print(s.host, s.port)'
)
backend_host="${HOST:-$configured_host}"
backend_port="${PORT:-$configured_port}"
.venv/bin/python -m uvicorn backend.app.main:app --host "$backend_host" --port "$backend_port" &
backend_pid=$!
(cd frontend && npm run dev -- --host 127.0.0.1) &
frontend_pid=$!

cleanup() {
  kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Backend:  http://${backend_host}:${backend_port}"
echo "Frontend: http://127.0.0.1:5173"
wait -n "$backend_pid" "$frontend_pid"
