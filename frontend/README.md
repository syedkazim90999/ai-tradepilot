# AI TradePilot — Frontend

Next.js 14 (App Router) + TypeScript + Tailwind CSS + hand-written shadcn/ui-style
components. Dark fintech theme. Charts: `lightweight-charts` (price candles) and
Recharts (P&L analytics).

## Run

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL (default http://localhost:8000)
npm run dev                        # http://localhost:3000
```

Production (low-memory build, as used on this VM):

```bash
NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=1024 npm run build
NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=1024 npm start   # port 3000
npm run lint
```

## Structure

- `app/` — public pages (`/`, `/features`, `/how-it-works`, `/pricing`, `/about`,
  `/contact`, `/faq`, `/terms`, `/privacy`, `/risk-disclosure`), auth pages
  (`/login`, `/register`, `/forgot-password`, `/reset-password`), user dashboard
  (`/dashboard/*`), admin panel (`/admin/*`, login at `/admin/login`).
- `lib/api.ts` — typed fetch client for the FastAPI backend. JWT access token in
  `localStorage` (`tp_access_token`, refresh `tp_refresh_token`); admin uses a
  separate token (`tp_admin_token`) from `POST /api/v1/admin/login`. 401 clears
  tokens and redirects to `/login` (or `/admin/login` for admin calls).
- `components/ui/` — button, card, input, label, badge, table, dialog, tabs,
  select, switch, alert, skeleton (shadcn/ui-style, written by hand — no CLI).
- `components/layout/` — site header/footer, dashboard + admin shells,
  `PriceChart` (lightweight-charts), `PnlChart` (Recharts).

## Honesty rules enforced in the UI

- Every number comes from the backend or is shown as an explicit empty state.
  No fabricated profits, users, or win rates anywhere.
- Dashboard overview shows only what `GET /api/v1/dashboard/overview` returns
  (open positions, total trades, realized P&L, unread notifications, latest
  signals). Balance, win rate, max drawdown and volume are **not** shown — the
  API does not expose them — and the page says so.
- The price chart renders real candles only when candle data is supplied. The
  backend has no klines endpoint, so it currently shows a labelled
  "Chart unavailable — no chart data is simulated" state.
- Pricing pages show the backend's real plan limits (Free $0 / Basic $19 /
  Pro $49 / Premium $99) and state that paid checkout is "coming soon".

## Known backend gaps (surfaced in the UI, not papered over)

- No klines/candles endpoint → chart empty state (see above).
- No contact-form endpoint → contact page composes a `mailto:` draft.
- No profile-update / password-change / 2FA-setup endpoint → Settings shows
  profile + 2FA status and says what is unavailable; password reset goes
  through the forgot-password flow.
- Admin overview returns only total users / active bots / open positions /
  total trades → suspended counts, connected accounts, volume and aggregate
  P&L are noted as unavailable, not estimated.
- No admin signal-history / strategy-performance endpoint → noted on
  `/admin/bots`; admin trades support only a limit query, so symbol/side/user
  filters there are client-side over the loaded rows (labelled on the page).
- The scanner can emit a `WAIT` direction as well as `LONG`/`SHORT`; the UI
  styles all three distinctly.
