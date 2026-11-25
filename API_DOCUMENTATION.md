# AI TradePilot — API Documentation

Generated from the live OpenAPI spec: start the backend and open
`http://localhost:8000/docs` (Swagger UI) or fetch `/openapi.json`.
**Verified 2026-11-25: 58 paths, 61 operations.** Endpoints marked
**(new)** were added in the 2026-11-25 gap-closure pass. No endpoint is
documented here that is not in the spec.

Base URL: `http://localhost:8000` (or `NEXT_PUBLIC_API_URL`).
All `/api/v1/*` user/admin endpoints except the public ones below require
`Authorization: Bearer <token>`.

## Auth flow

1. `POST /api/v1/auth/register` → 201, returns the user + (dev only) an
   email-verification token. Verify with `POST /auth/verify-email`.
2. `POST /api/v1/auth/login` with `{email, password, totp_code?}` →
   `{access_token, refresh_token, token_type: "bearer"}`. Access tokens live
   30 minutes; refresh tokens 7 days. If the user has 2FA enabled, a valid
   TOTP code is required.
3. Send `Authorization: Bearer <access_token>` on every call.
4. On expiry, `POST /api/v1/auth/refresh` with the refresh token — the old
   refresh token is rotated (single use). `POST /api/v1/auth/logout` revokes
   all sessions; `DELETE /api/v1/auth/sessions/{id}` revokes one.
5. Super Admin is a separate login: `POST /api/v1/admin/login` returns an
   `admin_access` token (30 min). User tokens cannot call admin endpoints
   and admin tokens cannot call user endpoints.
6. First-run admin setup: `POST /api/v1/auth/setup-admin` — works once only
   (409 once an admin exists).

## Error format

```json
{"detail": "Invalid email or password"}
```

- `401` — missing/invalid/expired token, or revoked session.
- `403` — suspended/disabled account, or wrong token type (user token on an
  admin endpoint).
- `404` — resource not found, or not owned by the caller (ownership is
  enforced: user A gets 404 for user B's trades, connections, notifications).
- `409` — duplicate email / admin already exists.
- `422` — validation error (bad UUID, bad enum, short password…).
- `429` — rate limited (login 10/min per IP; contact form 5/min; nginx adds
  100 req/min API / 10/min login).
- `502` — Binance is unreachable (klines proxy).

## Endpoints

### System

| Method & path | Purpose |
|---|---|
| `GET /health` | Status: `status`, `database`, `worker`, `exchange_reachable`, `testnet`. Public. |
| `GET /` | App name/version, link to `/docs`. Public. |

### Auth

| Method & path | Purpose |
|---|---|
| `POST /api/v1/auth/register` | Register (email, password ≥ 8, full_name). 201. |
| `POST /api/v1/auth/verify-email` | Verify email with the token from register. |
| `POST /api/v1/auth/login` | Login → access + refresh tokens. Rate-limited. |
| `POST /api/v1/auth/logout` | Revoke all of the caller's sessions. |
| `POST /api/v1/auth/refresh` | Rotate refresh token → new token pair. |
| `POST /api/v1/auth/forgot-password` | Request reset (always 200; dev returns the token). |
| `POST /api/v1/auth/reset-password` | Reset with token + new password. |
| `POST /api/v1/auth/setup-admin` | First-run Super Admin creation (once only). |
| `GET /api/v1/auth/me` | Current user profile. |
| `PUT /api/v1/auth/me` **(new)** | Update profile (currently `full_name`). |
| `POST /api/v1/auth/change-password` **(new)** | Change password (verifies current password). |
| `POST /api/v1/auth/2fa/setup` **(new)** | Generate TOTP secret; returns `otpauth_uri` + `secret` once (never logged). |
| `POST /api/v1/auth/2fa/verify` **(new)** | Verify a TOTP code → 2FA becomes active. |
| `POST /api/v1/auth/2fa/disable` **(new)** | Disable 2FA (requires current password, optional code). |
| `GET /api/v1/auth/sessions` | List the caller's sessions. |
| `DELETE /api/v1/auth/sessions/{session_id}` | Revoke one of the caller's sessions. |

### Market (public)

| Method & path | Purpose |
|---|---|
| `GET /api/v1/market/klines?symbol=BTCUSDT&interval=1h&limit=100` **(new)** | Binance Testnet public klines (no credentials). Allowed intervals: `1m 3m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M`; limit 1–1000. Cached in memory for 60 s per symbol/interval/limit. Returns `[{open_time, open, high, low, close, volume, close_time}]`. 502 if Binance is unreachable. |

### Contact (public)

| Method & path | Purpose |
|---|---|
| `POST /api/v1/contact` **(new)** | Store a contact message `{name, email, message}` → 201. Rate-limited (5/min). |

### Connections (Binance)

| Method & path | Purpose |
|---|---|
| `GET /api/v1/connections` | List the caller's connections (keys masked `****`+last4). |
| `POST /api/v1/connections` | Add a connection (keys encrypted with Fernet). 201. |
| `POST /api/v1/connections/{conn_id}/validate` | Validate against Binance; refuses keys with withdrawal permission. |
| `DELETE /api/v1/connections/{conn_id}` | Delete a connection. |

### Bot, signals, dashboard, trades

| Method & path | Purpose |
|---|---|
| `GET /api/v1/bot/settings` | Effective bot settings (creates defaults on first read). |
| `PUT /api/v1/bot/settings` | Update risk settings (risk %, daily loss %, max positions/leverage, symbols…). |
| `POST /api/v1/bot/start` / `POST /api/v1/bot/stop` | Enable/disable the bot (refused if admin-paused). |
| `GET /api/v1/signals?symbol=&limit=` | Latest signals (LONG/SHORT/WAIT), newest first. |
| `GET /api/v1/dashboard/overview` | User overview: open positions, total/closed trades, realised P&L, unread notifications, latest signals, **trading volume, win rate, max drawdown** (computed from real closed trades; win rate `null` when no closed trades), **available_balance** (USDT, only when a Binance account is connected; `null` + `available_balance_status: no_binance_connection|fetch_failed|ok` otherwise — never invented). |
| `GET /api/v1/trades?limit=` | Caller's trades, newest first. |
| `GET /api/v1/trades/{trade_id}` | One trade (404 if not the caller's). |
| `GET /api/v1/positions` | Caller's open positions. |
| `GET /api/v1/orders?limit=` | Caller's orders. |
| `GET /api/v1/notifications` | Caller's notifications. |
| `POST /api/v1/notifications/{notif_id}/read` | Mark a notification read. |
| `GET /api/v1/scanner/run?symbols=` | Trigger a scan (default symbols if omitted). |
| `GET /api/v1/scanner/status` | Scanner status + last signal time. |
| `GET /api/v1/subscriptions/plans` | Plan definitions (Free/Basic/Pro/Premium). |
| `GET /api/v1/subscriptions/me` | Caller's subscription (creates Free on first read). |

### Admin (`/api/v1/admin/*`, admin token required)

| Method & path | Purpose |
|---|---|
| `POST /api/v1/admin/login` | Admin login → `admin_access` token. |
| `GET /api/v1/admin/overview` | Totals: users, active bots, open positions, total trades, **suspended users, connected Binance accounts, total trading volume, aggregate realised P&L** (all computed from the DB; zeros when empty). |
| `GET /api/v1/admin/users?search=&limit=` | List users (no password hashes or secrets). |
| `GET /api/v1/admin/users/{user_id}` | One user. |
| `POST /api/v1/admin/users/{user_id}/suspend` | Suspend a user (audited). |
| `POST /api/v1/admin/users/{user_id}/reactivate` | Reactivate a user (audited). |
| `GET /api/v1/admin/trades?limit=` | All trades (limit only; filters are client-side in the UI). |
| `GET /api/v1/admin/positions` | All open positions. |
| `GET /api/v1/admin/signals?symbol=&direction=&date_from=&date_to=&limit=&offset=` **(new)** | Signal history from `market_signals`, filterable + paginated (`{total, limit, offset, signals}`). |
| `GET /api/v1/admin/strategies/performance` **(new)** | Strategy performance from real trades/signals only: totals, signals by direction, win rate, realised P&L, per-strategy breakdown (plus an "unassigned (scanner)" row). Zeros/`null` when empty — never estimates. |
| `POST /api/v1/admin/bots/pause-all` / `resume-all` | Pause/resume all bots (audited). |
| `POST /api/v1/admin/bots/{user_id}/pause` / `resume` | Pause/resume one user's bot (audited). |
| `GET /api/v1/admin/audit-logs?limit=` | Append-only admin audit log. |
| `GET /api/v1/admin/system/health` | DB + exchange reachability + environment. |
| `GET /api/v1/admin/settings` | All system settings. |
| `PUT /api/v1/admin/settings/{key}` | Set a system setting (audited). |
| `POST /api/v1/admin/maintenance` | Toggle maintenance mode (audited). |
| `POST /api/v1/admin/live-trading/activate` | Enable LIVE trading — requires `confirm=true` and acknowledgement `"I understand live trading risks real money"` (audited). |
| `POST /api/v1/admin/live-trading/deactivate` | Disable live trading (audited). |

## Rate limits

- Login: 10 requests/min per IP (in-memory limiter + nginx zone).
- Contact form: 5 requests/min per IP.
- API via nginx: 100 requests/min per IP (burst 20).
- Binance client: exponential backoff on 429/418, respects `Retry-After`.

## Testnet vs production

- Default base URLs are Binance **Testnet** (`testnet.binancefuture.com`).
  Public endpoints (klines, exchange info, tickers) need no credentials.
- Signed endpoints need a validated connection; validation refuses keys with
  withdrawal permission.
- Live trading stays disabled until a Super Admin activates it explicitly
  (see the admin endpoint above) **and** the connection environment is
  `live` **and** the user opted in. The trading engine enforces all three.
