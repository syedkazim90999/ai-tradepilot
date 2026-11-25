# AI TradePilot — Installation

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12 | Backend + tests |
| Node.js / npm | 20+ / 10+ (dev VM: Node 24, npm 10.9.4) | Frontend |
| Docker + Compose plugin | any recent | Production deploy only |
| PostgreSQL 16, Redis 7 | — | Provided by `docker-compose.yml`; **not** required for local dev |
| Binance Futures Testnet keys | — | Only for connecting a real account; scanner/klines work without keys |

Network: the dev VM routes through an authenticating egress proxy
(`HTTPS_PROXY` env). pip/npm use the proxy env vars as-is. The backend
normalises a bare `host:port` proxy value for httpx/websockets (see
`app/services/binance_client.py::_proxy_url`).

## A. Local development (SQLite fallback)

```bash
cd ai-tradepilot

# 1. Backend venv + dependencies
python3 -m venv backend/venv
backend/venv/bin/pip install -r backend/requirements.txt

# 2. Environment (optional for dev — defaults are SQLite + dev SECRET_KEY)
cp backend/.env.example backend/.env
# Edit backend/.env: set a real SECRET_KEY and FERNET_KEY for anything
# beyond throwaway testing. Generate a Fernet key with:
#   cd backend && ./venv/bin/python scripts/generate_fernet_key.py

# 3. Migrations (creates backend/tradepilot.db on first run)
cd backend && ./venv/bin/alembic upgrade head && cd ..

# 4. Frontend
cd frontend && npm install && cd ..

# 5. Run both (or use ./scripts/dev.sh, which does steps 3–5)
# Terminal 1:
cd backend && ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Terminal 2:
cd frontend && npm run dev
# Backend: http://localhost:8000  (interactive docs: /docs)
# Frontend: http://localhost:3000
```

Create the Super Admin once (first run only; fails with 409 afterwards):

```bash
curl -X POST http://localhost:8000/api/v1/auth/setup-admin \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<12+ chars>"}'
```

### Tests

```bash
cd backend
./venv/bin/pytest tests/ -q        # full suite (77 tests, ~30 s)
./venv/bin/pytest tests/test_smoke.py -q
```

Tests use an isolated scratch SQLite DB (`/tmp/test_tradepilot.db`) via a
`get_db` dependency override — they never touch `backend/tradepilot.db`.
Exchange tests use mocked Binance responses; no real credentials are used.

### Low-memory notes

The dev VM has ~650 MB free. Run things **sequentially**: never the backend
server + Next.js build + pytest at once. For the frontend build use:

```bash
NODE_OPTIONS=--max-old-space-size=1024 NEXT_TELEMETRY_DISABLED=1 npm run build
```

## B. VPS / Docker deployment

```bash
# On the VPS (Ubuntu 22.04/24.04):
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git
git clone <repo> ai-tradepilot && cd ai-tradepilot

cp backend/.env.example .env
# Edit .env and set REAL values:
#   SECRET_KEY=<long random>  FERNET_KEY=<from generate_fernet_key.py>
#   POSTGRES_PASSWORD=<strong>  NEXT_PUBLIC_API_URL=https://yourdomain.com
./scripts/deploy-prod.sh
# The script REFUSES to deploy with placeholder secrets, a missing .env,
# a .env committed to git, or live trading enabled without --confirm-live.
```

What the deploy does: `docker compose build`, `up -d` (postgres, redis,
backend with `alembic upgrade head` before uvicorn, celery worker,
frontend standalone, nginx). Check health:

```bash
curl http://localhost:8000/health
docker compose ps
docker compose logs backend
```

### TLS (nginx)

1. Point your domain at the VPS and open ports 80/443.
2. Obtain a certificate (the nginx config has an ACME webroot location):
   ```bash
   docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d yourdomain.com
   # or on the host: certbot certonly --webroot -w <path> -d yourdomain.com
   cp /etc/letsencrypt/live/yourdomain.com/{fullchain.pem,privkey.pem} nginx/certs/
   ```
3. Uncomment the 443 server block in `nginx/nginx.conf` and
   `docker compose restart nginx`.

### Backups

```bash
./scripts/backup.sh            # pg_dump + .env copy into ./backups/<date>/
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `apt-get install postgresql/redis-server` fails with "Unable to locate package" | Stale apt lists behind the proxy. **Do not keep retrying** — local dev uses SQLite; Postgres/Redis come from Docker on the deploy host. |
| Backend won't start: `FERNET_KEY is not set` | Only when creating a Binance connection. Generate one: `cd backend && ./venv/bin/python scripts/generate_fernet_key.py`, put it in `backend/.env`. |
| `/health` shows `exchange_reachable: false` | Testnet unreachable through the proxy/firewall. Public klines/scanner need outbound HTTPS to `testnet.binancefuture.com`. |
| `next build` OOM / killed | Use the low-memory flags above; close the backend server first. |
| pytest failures about `_Session is None` | Old checkout — `tests/__init__.py` must exist (pytest must import conftest as `tests.conftest`). |
| Alembic test touches the dev DB | Fixed: the migration test runs Alembic in a subprocess with `DATABASE_URL` set to a scratch file. |
| Login returns 429 | In-memory rate limit (10 logins/min per IP). Wait a minute; it resets on restart. |
| `SECRET_KEY` / placeholder refusal from deploy-prod.sh | Set real values in `.env` — see the script's error message. |
