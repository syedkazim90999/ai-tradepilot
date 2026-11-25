# AI TradePilot — DEVELOPMENT_STATUS.md

**Project:** AI TradePilot — AI-powered Binance Futures automated trading SaaS platform
**Location:** `~/workspace/ai-tradepilot/`
**Stack:** Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic, Next.js (TypeScript) + Tailwind + shadcn/ui, PostgreSQL, Redis, Docker.
**Environment:** Binance Futures **Testnet is the default**. Production trading is DISABLED by default and requires an explicit activation step.

## Phase status

| Phase | Description | Status |
|---|---|---|
| 1 | Project setup, repo, Docker, backend + frontend scaffolding | DONE (backend) |
| 2 | Database models, migrations, auth, Super Admin setup | DONE |
| 3 | Public website + user dashboard | DONE (2026-11-25, verified: `next build` clean, 33 routes, `next lint` clean, prod server smoke-tested) |
| 4 | Super Admin dashboard + permissions | DONE (2026-11-25, verified: admin pages built + live admin endpoints checked) |
| 5 | Binance Testnet integration | DONE |
| 6 | Market scanner + AI analysis | DONE (rule-based signals; no ML model yet) |
| 7 | Trading execution + risk management | DONE |
| 8 | Trade history, notifications, analytics | DONE (backend endpoints; frontend pending) |
| 9 | Automated tests, security review, bug fixing | DONE (2026-11-25: 77 pytest tests pass, 0 fail; see below) |
| 10 | Deployment docs + production readiness review | DONE (2026-11-25: Docker files, deploy/backup scripts, README/INSTALLATION/SECURITY/API docs written; Docker itself NOT run here — not installed) |

## Environment notes (verified 2026-11-25)

- Python 3.12.3, pip 24, Node v24.22.1, npm 10.9.4 available.
- Docker NOT installed; PostgreSQL and Redis NOT installed. Dockerfiles + docker-compose.yml are still delivered; local verification tries `sudo apt-get install -y postgresql redis-server` first, falls back to SQLite for local verification only (PostgreSQL remains the deployment target).
- Memory is tight (~650 MB free at check). Build and test SEQUENTIALLY; never run Postgres + Redis + Next.js build + pytest at once. Use low-memory Next.js build settings.
- Network goes through an authenticating egress proxy (HTTPS_PROXY env). pip uses the proxy env vars as-is.

## Decisions

- Modular monolith first; components kept modular for later microservice split.
- Indicators implemented in NumPy/Pandas (RSI, MACD, EMA 20/50/200, Bollinger Bands, ATR, VWAP) — no extra TA library dependency.
- Signals are deterministic rule-based; no LLM ever places orders.
- Conservative Testnet defaults: 0.5% risk/trade, 2% daily loss limit, max 2 positions, max 2x leverage, 2:1 reward/risk.
- API keys encrypted with Fernet (key from env, never committed). No plaintext passwords (Argon2id) or secrets in logs.

## API contract (backend <-> frontend)

Base: `http://localhost:8000` (or `NEXT_PUBLIC_API_URL`).
- `GET /health` — status, db, worker, exchange reachability.
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/verify-email`, `POST /api/v1/auth/forgot-password`, `POST /api/v1/auth/reset-password`, `POST /api/v1/auth/setup-admin` (first-run only, fails if an admin already exists), `GET /api/v1/auth/me`, `GET /api/v1/auth/sessions`, `DELETE /api/v1/auth/sessions/{id}`.
- **(new 2026-11-25)** `PUT /api/v1/auth/me` (update full_name), `POST /api/v1/auth/change-password`, `POST /api/v1/auth/2fa/setup` (returns otpauth URI + secret once), `POST /api/v1/auth/2fa/verify`, `POST /api/v1/auth/2fa/disable`.
- **(new 2026-11-25)** `GET /api/v1/market/klines?symbol=BTCUSDT&interval=1h&limit=100` (public Testnet klines, 60 s in-memory cache), `POST /api/v1/contact` (201, stores `contact_messages`).
- `GET/POST /api/v1/connections`, `POST /api/v1/connections/{id}/validate`, `DELETE /api/v1/connections/{id}` (masked key in responses).
- `GET/PUT /api/v1/bot/settings`, `POST /api/v1/bot/start`, `POST /api/v1/bot/stop`.
- `GET /api/v1/signals` (latest, filter by symbol), `GET /api/v1/dashboard/overview` (enriched 2026-11-25: + `closed_trades`, `trading_volume`, `win_rate` (null when no closed trades), `max_drawdown`, `available_balance` only with a connected Binance account — null + status otherwise, never invented), `GET /api/v1/trades`, `GET /api/v1/trades/{id}`, `GET /api/v1/positions`, `GET /api/v1/orders`.
- `GET /api/v1/notifications`, `POST /api/v1/notifications/{id}/read`.
- `GET /api/v1/scanner/run` (trigger), `GET /api/v1/scanner/status`.
- Admin (`/api/v1/admin/*`): `GET /admin/overview` (enriched 2026-11-25: + `suspended_users`, `connected_binance_accounts`, `total_trading_volume`, `aggregate_realized_pnl`), `GET /admin/users`, `GET /admin/users/{id}`, `POST /admin/users/{id}/suspend`, `POST /admin/users/{id}/reactivate`, `GET /admin/trades`, `GET /admin/positions`, `POST /admin/bots/pause-all`, `POST /admin/bots/resume-all`, `POST /admin/bots/{user_id}/pause`, `POST /admin/bots/{user_id}/resume`, `GET /admin/audit-logs`, `GET /admin/system/health`, `GET/PUT /admin/settings`, `POST /admin/maintenance`.
- **(new 2026-11-25)** `GET /api/v1/admin/signals` (filter symbol/direction/date, paginated), `GET /api/v1/admin/strategies/performance` (real trades/signals only; zeros/nulls when empty).
- Live OpenAPI spec verified 2026-11-25: **58 paths, 61 operations** (was 50 paths).
- `GET /api/v1/subscriptions/plans`, `GET /api/v1/subscriptions/me`.

## Known limitations (to be updated)

- **Frontend built and verified (2026-11-25):** `frontend/` — Next.js 14.2.33 (App Router) + TypeScript + Tailwind + hand-written shadcn/ui-style components, `lightweight-charts` + Recharts. `npm run build` succeeds (33 routes, First Load JS ~100–112 kB/route), `npm run lint` clean, production server smoke-tested (22 routes returned 200, unknown route 404). Live backend checks with a fresh test user (`frontend-test@example.com`, created 2026-11-25, left in the dev DB) confirmed all 12 user endpoints and all 7 admin endpoints used by the UI return 200 with real data. Both servers were stopped afterwards. Run: `cd frontend && npm install && npm run dev` (or `NODE_OPTIONS=--max-old-space-size=1024 npm run build && npm start`). See `frontend/README.md`.
- **Frontend gaps CLOSED 2026-11-25:** klines endpoint added → price chart on Dashboard and Signals pages loads real Testnet candles (empty state kept, labelled, no simulated data); contact form now POSTs to `/api/v1/contact`; Settings has working profile edit, password change and TOTP 2FA setup/verify/disable; admin overview shows suspended users, connected Binance accounts, trading volume and aggregate P&L; admin signal history + strategy performance endpoints exist (admin UI does not yet have pages for them — see below). Dashboard shows win rate, volume, max drawdown and available balance (null/"Not connected" when no Binance account — never estimated). Scanner can emit `WAIT` as well as `LONG`/`SHORT`; the UI styles all three distinctly.
- **Phase 9/10 completion (2026-11-25):** full pytest suite — **77 tests pass, 0 fail** (`cd backend && ./venv/bin/pytest tests/ -q`, ~31 s), covering auth (register/login/wrong password/Argon2id/session revocation/expired+invalid JWT/rate limiting), isolation (user A cannot read user B's trades/positions/orders/connections/settings/notifications; admin never sees secrets), trading (LONG on V-shape fixture, WAIT on flat/choppy, SHORT branch via mocked indicators, position-sizing math, daily-loss + max-positions + leverage blocks, duplicate-order prevention, SL/TP creation, partial fills), exchange (mocked klines, 429/418 backoff, websocket reconnect/exhaustion, reconciliation mismatch), system (Alembic upgrade/downgrade on a scratch DB, /health, OpenAPI lists all 8 new endpoints, worker recovery). Two latent bugs found and fixed by the tests: route handlers compared UUID columns to raw `str` path params (SQLAlchemy 500 on admin user suspend/get, trade/notification/connection lookups) — path params are now `uuid.UUID`. Smoke tests still pass (5/5) after all additions.
- **SHORT signal is near-unreachable with the current rules** (found while writing fixtures): RSI>65 cannot coexist with the sustained decline the other SHORT conditions need. The SHORT rule branch is tested via mocked indicators; consider re-tuning the rules before relying on SHORT signals.
- **Docker (2026-11-25):** backend Dockerfile rewritten (multi-stage, Python 3.12-slim, non-root, healthcheck); frontend Dockerfile added (multi-stage Node 20, standalone output — verified: `npm run build` with `output: "standalone"` produces `.next/standalone/server.js`); root `docker-compose.yml` rewritten (postgres:16, redis:7, backend, worker, frontend, nginx; named volumes; healthchecks; `depends_on` with `condition: service_healthy`; env via `.env`, no hardcoded secrets); `nginx/nginx.conf` added (reverse proxy /api → backend, / → frontend, rate-limit zones, security headers, TLS-ready commented certbot section); `scripts/dev.sh`, `scripts/deploy-prod.sh` (refuses placeholder/missing secrets, `.env` committed to git, live trading without `--confirm-live`), `scripts/backup.sh` (pg_dump + .env copy). **Docker was NOT run here — Docker is not installed on the dev VM; compose YAML was validated with `python -c yaml` only.**
- **Docs (2026-11-25):** root `README.md`, `INSTALLATION.md`, `SECURITY.md`, `API_DOCUMENTATION.md` (from the live OpenAPI spec: 58 paths, 61 operations) written; `backend/.env.example` extended (POSTGRES_*, NEXT_PUBLIC_API_URL, token lifetimes, commented SMTP placeholders).
- **PostgreSQL/Redis NOT installed locally (2026-11-25):** `apt-get update` hung for 10+ min through the egress proxy and a later bounded install failed with `E: Unable to locate package postgresql / redis-server` (stale/incomplete apt lists). Local verification therefore used **SQLite** (`sqlite+aiosqlite:///./tradepilot.db`); PostgreSQL remains the deployment target — `docker-compose.yml` and `DATABASE_URL=postgresql+psycopg://...` in `.env.example` are ready. The autogenerated Alembic migration was edited to use plain `sa.JSON()` instead of the PostgreSQL `JSONB` variant so it runs on SQLite; on Postgres it will store JSON (not JSONB) unless the migration is regenerated.
- **No ML confirmation model yet:** signals are deterministic rule-based only; the optional scikit-learn logistic-regression confirmation was not added. scikit-learn is in requirements.txt for a later agent.
- **Email is dev-only:** verification/reset tokens are logged and returned in the dev response; no real SMTP is wired.
- **Proxy quirk (fixed in code):** the VM's `HTTPS_PROXY` is a bare `host:port` with no scheme, which httpx rejects (`Invalid port`). `app/services/binance_client.py` normalizes it by prepending `http://` for both httpx and websockets.
- **Test data in the local DB:** the smoke tests and live curl checks created users `smoke@example.com`, `live@example.com` and admin `admin@example.com` (password `AdminPass123456`, test-only) in `backend/tradepilot.db`. Delete the file and re-run `alembic upgrade head` for a clean DB.
- Live trading is DISABLED by default and requires explicit Super Admin activation (`POST /api/v1/admin/live-trading/activate` with the exact acknowledgement phrase). No real Binance API keys have been connected; private endpoints are untested against a live account.

## Remaining production requirements (after 2026-11-25)

- Run `docker compose up` end-to-end on a Docker host (not possible on the dev VM) and verify all healthchecks pass; obtain TLS certificates and uncomment the 443 block in `nginx/nginx.conf`.
- Wire real SMTP and stop returning email-verification/reset tokens in API responses (currently dev-only leak — see SECURITY.md).
- Connect real Binance Testnet API keys and test signed endpoints (account info, order placement) against a live Testnet account; private endpoints are still untested against a live account.
- Add admin UI pages for signal history and strategy performance (endpoints exist; no frontend pages yet).
- Admin trades page still filters client-side (limit-only endpoint).
- Fernet key rotation procedure is documented but not automated; no Redis password in compose; in-memory rate limiter is per-process.
- No ML confirmation model yet (signals are rule-based only); SHORT rule branch needs re-tuning (see above).
