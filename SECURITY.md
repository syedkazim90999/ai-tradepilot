# AI TradePilot — Security

## Threat model

AI TradePilot holds the keys to users' Binance accounts and can place
orders with real money. The assets at risk, in order:

1. **Binance API keys/secrets** (per user, encrypted at rest) — theft =
   unauthorised trading on the user's account.
2. **User passwords / sessions** — account takeover, then (1).
3. **JWT / admin tokens** — privilege escalation to Super Admin, including
   enabling live trading for everyone.
4. **Database contents** — trades, P&L, emails, audit logs.
5. **Availability** — scanner/worker downtime, Binance rate-limit bans
   (429/418) affecting all users.

Out of scope for this document: Binance's own security, the user's device,
and the VPS provider's physical security.

## Controls in place

- **Passwords — Argon2id** (`argon2-cffi`, default parameters). No plaintext
  passwords anywhere; hashes start with `$argon2id$`. Verified by tests.
- **Binance secrets — Fernet** (AES-128-CBC + HMAC, `cryptography`).
  Keys are encrypted before storage; responses show only `****` + last 4.
  Admin endpoints never return encrypted or plaintext secrets (tested).
  A connection whose key has **withdrawal permission is refused** at
  validation time.
- **Fernet key management** — `FERNET_KEY` comes from the environment only,
  never committed (`.env` is git-ignored; `deploy-prod.sh` refuses an empty
  key). **Rotation procedure:** generate a new key, decrypt every stored
  `api_key_encrypted`/`api_secret_encrypted` with the old key and
  re-encrypt with the new key in a one-off migration script, then replace
  the env var and restart. There is no automatic rotation yet — rotating
  without re-encrypting stored rows **breaks all connections** (decrypt
  raises `InvalidToken`). Keep the old key backed up in a password manager
  until rotation is verified.
- **JWT / sessions** — HS256, access tokens 30 min, refresh tokens 7 days.
  Every token's `jti` has a server-side `user_sessions` row; logout revokes
  all sessions, single sessions can be revoked, refresh rotates (old token
  dies). Expired/invalid/wrong-type tokens are rejected (tested). Admin
  tokens are a separate type (`admin_access`) and cannot be used as user
  tokens or vice versa.
- **2FA (TOTP)** — `pyotp`, setup returns the otpauth URI + secret **once**,
  never logged; verification required before 2FA activates; login requires
  the code when enabled; disable requires the current password.
- **CORS** — allow-list from `CORS_ORIGINS` (default localhost:3000/8000);
  credentials allowed only for those origins.
- **CSRF** — the API is token-based (Bearer header, no cookies), so classic
  cookie CSRF does not apply. If cookie auth is ever added, CSRF tokens
  become mandatory.
- **Rate limiting** — in-memory per-IP+path limiter on login (10/min) and
  the public contact form (5/min); nginx adds 100 req/min (API) and
  10/min (login) zones in front. Note: the in-memory limiter is per-process
  and resets on restart — it is not a substitute for a shared limiter
  (Redis) at scale.
- **Binance rate limits** — the client backs off exponentially on 429/418
  and respects `Retry-After` (tested with mocks).
- **Audit logs** — every sensitive admin action (suspend/reactivate,
  pause/resume, setting changes, live-trading activation, maintenance)
  writes an append-only `admin_audit_logs` row with admin id, IP and details.
- **Live-trading guard** — live trading is DISABLED by default
  (`live_trading_enabled=false` in `system_settings`). Enabling it needs
  Super Admin + `confirm=true` + the exact acknowledgement phrase, and the
  engine also requires the connection environment to be `live` and the user
  to have opted in (`bot_settings.trading_enabled`). `deploy-prod.sh`
  refuses a `.env` with live trading on unless `--confirm-live` is passed.
- **Input validation** — Pydantic schemas on every endpoint; UUID path
  params are parsed as UUIDs (a string that is not a UUID is a 422, not a
  500); symbol/interval allow-lists on the klines endpoint.
- **Secrets handling rules** — never log secrets, tokens, or API keys;
  never return them in responses; never commit `.env`; never put secrets
  in URLs. The contact form has no secret fields by design.

## What is NOT yet production-hardened

- **No real SMTP** — email verification/reset tokens are logged and returned
  in dev responses. In production this leaks tokens to anyone who can read
  the response/logs. Wire SMTP + stop returning tokens before going live.
- **Dev SECRET_KEY default** — `CHANGE_ME_dev_only_do_not_use_in_production`
  is the fallback if no env var is set. `deploy-prod.sh` refuses it, but a
  manual `docker compose up` would not.
- **No HTTPS by default** — TLS is commented out in `nginx/nginx.conf`
  until certificates are installed. Never expose the stack over plain HTTP
  outside localhost.
- **In-memory rate limiter** — per-process only; use Redis/slowapi shared
  state before multi-instance deployment.
- **No WAF / intrusion detection, no automated dependency scanning** —
  add `pip-audit` / `npm audit` to CI.
- **No automated Fernet rotation, no secret versioning.**
- **Celery broker has no auth** — Redis is not exposed publicly in the
  compose file, but set a Redis password for any shared network.
- **Backups are unencrypted** — `scripts/backup.sh` copies `.env` next to
  the dump; store backup directories encrypted and off-host.
- **No ML confirmation model** — signals are rule-based only; the SHORT
  branch is near-unreachable with the current rules (RSI>65 cannot coexist
  with the sustained decline the other conditions need). Treat all signals
  as rule outputs, not predictions; the confidence score is rule agreement,
  not a probability of profit.

## Reporting a vulnerability

Email the project maintainer with: affected version/commit, steps to
reproduce, and impact. Do **not** open a public issue for a live
vulnerability. Please allow time to fix before any disclosure; a fix and
a security note will be published in DEVELOPMENT_STATUS.md.
