# AI TradePilot

AI-powered **Binance Futures automated trading SaaS** — multi-user, with a
rule-based market scanner, risk-managed execution, and a Super Admin panel.
**Binance Testnet is the default. Live trading is DISABLED by default** and
requires an explicit Super Admin activation step. No LLM ever places orders:
signals are deterministic rules over RSI, MACD, EMA, Bollinger Bands, ATR
and VWAP.

> ⚠️ **Testnet-first warning.** This platform can lose real money if live
> trading is enabled. Never enable live trading with an API key that has
> withdrawal permission, never trade with money you cannot afford to lose,
> and read [SECURITY.md](SECURITY.md) before any production deployment.

## Features

- **Auth** — email registration/login, JWT access + refresh tokens with
  server-side session records (revocable), Argon2id passwords, TOTP 2FA,
  profile/password management, email verification + password reset (dev:
  tokens returned in the response; no SMTP wired yet).
- **Binance connections** — API keys encrypted with Fernet, masked display,
  permission validation (withdrawal permission is refused).
- **Market scanner** — multi-timeframe (5m/15m/1h/4h) scan of USDT-M
  perpetuals; emits `LONG` / `SHORT` / `WAIT` signals with entry, stop-loss
  (1.5×ATR), take-profit (2:1 reward/risk) and a rule-agreement confidence
  score (not a probability of profit). Public klines endpoint
  (`GET /api/v1/market/klines`) powers the price charts.
- **Risk-managed execution** — 0.5% risk/trade, 2% daily loss limit, max 2
  positions, max 2× leverage by default; global emergency stop; idempotent
  orders (deterministic `clientOrderId`, DB unique constraint); SL/TP
  reduce-only orders; execution always verified via order status; position
  reconciliation against the exchange.
- **Dashboards** — user overview (real volume, win rate, max drawdown,
  available balance only when a Binance account is connected), trades,
  positions, orders, notifications; Super Admin overview (suspended users,
  connected accounts, volume, aggregate P&L), signal history, strategy
  performance (computed from real trades/signals only), audit logs,
  system health, maintenance mode, bot pause/resume.
- **Subscriptions** — Free/Basic/Pro/Premium plan definitions (payments are
  a stub — no provider is wired yet).

## Architecture

```
                    ┌─────────────────────┐
                    │  nginx (reverse     │  :80 / :443 (TLS-ready)
                    │  proxy, rate limit) │
                    └──────┬──────┬───────┘
                           │      │
              ┌────────────┘      └────────────┐
              ▼                                ▼
   ┌──────────────────┐              ┌──────────────────┐
   │ Next.js frontend │              │ FastAPI backend  │──▶ Binance Testnet
   │ (standalone)     │              │ + in-app worker  │    (public + signed)
   └──────────────────┘              └──────┬───────┬───┘
                                            │       │
                                   ┌────────┘       └────────┐
                                   ▼                         ▼
                            PostgreSQL 16            Redis 7 / Celery
                            (alembic migrations)     (scanner + reconcile)
```

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2 (async) + Alembic,
  `backend/app/` — `api/routes/` (auth, connections, user, admin, market,
  contact), `services/` (binance_client, scanner, signals, indicators,
  risk, trading, notifications), `worker/` (Celery tasks).
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind +
  shadcn/ui-style components, `lightweight-charts` + Recharts,
  `frontend/app/` (33 routes) + `frontend/lib/api.ts`.
- **Tests:** pytest, `backend/tests/` — 77 tests (see below).

## Quick start

**Local dev (SQLite fallback, no Docker/Postgres needed):**

```bash
./scripts/dev.sh
# backend: http://localhost:8000 (docs: /docs)   frontend: http://localhost:3000
```

Manual equivalent — see [INSTALLATION.md](INSTALLATION.md).

**Docker (production stack, needs a Docker host):**

```bash
cp backend/.env.example .env   # fill in real SECRET_KEY / FERNET_KEY / POSTGRES_PASSWORD
./scripts/deploy-prod.sh
```

## Project structure

```
ai-tradepilot/
├── backend/            FastAPI app, alembic/, tests/, Dockerfile, .env.example
├── frontend/           Next.js app, Dockerfile (standalone output)
├── nginx/nginx.conf    reverse proxy + rate limits + TLS-ready
├── scripts/            dev.sh, deploy-prod.sh, backup.sh
├── docker-compose.yml  postgres, redis, backend, worker, frontend, nginx
├── README.md  INSTALLATION.md  SECURITY.md  API_DOCUMENTATION.md
└── DEVELOPMENT_STATUS.md
```

## Test status (verified 2026-11-25)

- **77 pytest tests pass, 0 fail** — `cd backend && ./venv/bin/pytest tests/ -q`
  (auth, isolation, trading, exchange-with-mocks, system, new endpoints;
  smoke tests included). See `backend/tests/` and DEVELOPMENT_STATUS.md.
- **Frontend:** `npm run build` clean, 33 routes; `npm run lint` clean.
- **Live check:** `/health` returns `ok` (DB ok, worker ok, exchange
  reachable, testnet true); `GET /api/v1/market/klines?symbol=BTCUSDT`
  returns real Testnet candles.
- **Docker was NOT run here** (Docker is not installed on the dev VM):
  `docker-compose.yml` was validated for YAML syntax only.

## Docs

- [INSTALLATION.md](INSTALLATION.md) — local dev + VPS/Docker setup, troubleshooting.
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) — full endpoint reference from the live OpenAPI spec.
- [SECURITY.md](SECURITY.md) — threat model, key management, what is not yet production-hardened.
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) — phase status, decisions, known limitations.
- [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md) — component notes.
