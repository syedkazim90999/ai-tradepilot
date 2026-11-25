#!/usr/bin/env bash
# AI TradePilot — backup: pg_dump of the Postgres service + data dir snapshot.
# Usage: ./scripts/backup.sh [output-dir]   (default: ./backups/<date>)
# Restores are manual: psql < dump.sql  (see INSTALLATION.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${1:-$ROOT/backups/$(date +%Y-%m-%d_%H%M)}"
mkdir -p "$OUT"
# Load .env so POSTGRES_USER/DB match the running stack.
set -a; [ -f .env ] && . ./.env; set +a
command -v docker >/dev/null || { echo "docker is not installed — nothing to back up." >&2; exit 1; }
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-tradepilot}" -d "${POSTGRES_DB:-tradepilot}" > "$OUT/tradepilot.sql"
echo "Postgres dump: $OUT/tradepilot.sql ($(du -h "$OUT/tradepilot.sql" | cut -f1))"
# Also back up the .env (contains secrets — store this directory securely, never in git).
cp .env "$OUT/.env.backup" 2>/dev/null || echo "WARNING: no .env found to back up."
echo "Backup complete: $OUT"
