# AI TradePilot — Backend

FastAPI + SQLAlchemy 2 + Alembic. Binance Futures **Testnet by default**; production trading is DISABLED unless explicitly activated by the Super Admin.

## Quick start (local, no Postgres/Redis needed)

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
# generate a Fernet key and put it in .env:
./venv/bin/python scripts/generate_fernet_key.py
./venv/bin/alembic upgrade head
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docs: http://localhost:8000/docs — Health: http://localhost:8000/health

With Postgres (deployment target): set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/tradepilot` in `.env`.

## First-run Super Admin

```bash
curl -X POST http://localhost:8000/api/v1/auth/setup-admin \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<12+ chars>"}'
```

Fails with 409 once an admin exists. Admin login: `POST /api/v1/admin/login`.

## Live trading

Disabled by default (`live_trading_enabled=false`). The Super Admin must call
`POST /api/v1/admin/live-trading/activate` with `{"confirm": true, "acknowledgement": "I understand live trading risks real money"}`.
The trading engine refuses live orders otherwise.

## Tests

```bash
./venv/bin/pytest tests -v
```
