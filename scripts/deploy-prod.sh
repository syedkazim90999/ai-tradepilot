#!/usr/bin/env bash
# AI TradePilot — production deploy (Docker Compose).
# REFUSES unsafe defaults before doing anything:
#   * missing .env, SECRET_KEY or FERNET_KEY
#   * placeholder/default secrets (CHANGE_ME / change_me / empty)
#   * live_trading_enabled=true without --confirm-live
#   * .env committed to git
# Usage: ./scripts/deploy-prod.sh [--confirm-live]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONFIRM_LIVE=false
[ "${1:-}" = "--confirm-live" ] && CONFIRM_LIVE=true

fail() { echo "DEPLOY REFUSED: $*" >&2; exit 1; }
command -v docker >/dev/null || fail "docker is not installed on this host."
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is not available."

[ -f .env ] || fail "missing .env at project root — copy backend/.env.example to .env and fill in real values."
grep -q '^SECRET_KEY=' .env || fail "SECRET_KEY is missing from .env."
grep -q '^FERNET_KEY=' .env || fail "FERNET_KEY is missing from .env."
SECRET_KEY="$(grep '^SECRET_KEY=' .env | cut -d= -f2-)"
FERNET_KEY="$(grep '^FERNET_KEY=' .env | cut -d= -f2-)"
case "$SECRET_KEY" in
  ""|*CHANGE_ME*|*change_me*|*dev_only*) fail "SECRET_KEY is still a placeholder/default — generate a long random value." ;;
esac
case "$FERNET_KEY" in
  "") fail "FERNET_KEY is empty — generate one with: cd backend && ./venv/bin/python scripts/generate_fernet_key.py" ;;
esac
if grep -q '^POSTGRES_PASSWORD=' .env; then
  PW="$(grep '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)"
  case "$PW" in ""|tradepilot|*change_me*) fail "POSTGRES_PASSWORD is empty or a default value." ;; esac
else
  fail "POSTGRES_PASSWORD is missing from .env."
fi
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    fail ".env is committed to git — remove it from version control (git rm --cached .env) before deploying."
  fi
fi
if grep -q '^LIVE_TRADING_ENABLED=true' .env; then
  [ "$CONFIRM_LIVE" = true ] || fail "LIVE_TRADING_ENABLED=true in .env — live trading risks real money. Re-run with --confirm-live only if you really mean it."
fi

echo "Prerequisites OK. Building and starting the stack..."
docker compose build
docker compose up -d
echo "Waiting for backend health..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then echo "Backend healthy."; break; fi
  [ "$i" = 30 ] && fail "backend did not become healthy in time — check: docker compose logs backend"
  sleep 2
done
docker compose ps
echo "Deployed. API: http://localhost:8000/health — create the Super Admin once via POST /api/v1/auth/setup-admin."
