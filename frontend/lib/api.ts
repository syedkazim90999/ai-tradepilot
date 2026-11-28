// AI TradePilot API client — typed fetch wrapper against the FastAPI backend.
// Base URL: NEXT_PUBLIC_API_URL (default http://localhost:8000).
// Auth: JWT access token in localStorage ("tp_access_token"), refresh token
// ("tp_refresh_token"). Admin uses a separate token ("tp_admin_token") issued
// by POST /api/v1/admin/login (token type "admin_access").
// 401 -> tokens cleared and the browser is redirected to /login.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ACCESS_KEY = "tp_access_token";
const REFRESH_KEY = "tp_refresh_token";
const ADMIN_KEY = "tp_admin_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}
export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ADMIN_KEY);
}
export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function setAdminToken(token: string) {
  localStorage.setItem(ADMIN_KEY, token);
}
export function clearAuth() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(ADMIN_KEY);
}
export function isLoggedIn(): boolean {
  return !!getAccessToken();
}
export function isAdminLoggedIn(): boolean {
  return !!getAdminToken();
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type FetchOpts = {
  method?: string;
  body?: unknown;
  admin?: boolean;
  /** Do not redirect to /login on 401 (used by the login call itself). */
  noAuthRedirect?: boolean;
};

async function apiFetch<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const token = opts.admin ? getAdminToken() : getAccessToken();
  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401 && !opts.noAuthRedirect && typeof window !== "undefined") {
    clearAuth();
    window.location.href = opts.admin ? "/admin/login" : "/login";
    throw new ApiError(401, "Session expired — please sign in again.");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") msg = data.detail;
      else if (Array.isArray(data?.detail)) msg = data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ") || msg;
    } catch {
      /* keep default message */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------------------------------------------------------------- types
export interface UserOut {
  id: string; email: string; full_name: string | null; is_active: boolean;
  is_suspended: boolean; is_email_verified: boolean; totp_enabled: boolean; created_at: string;
}
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; }
export interface SessionOut { id: string; token_type: string; is_revoked: boolean; ip_address: string | null; expires_at: string; created_at: string; }
export interface ConnectionOut {
  id: string; exchange: string; environment: string; api_key_masked: string; label: string | null;
  is_active: boolean; can_trade: boolean; can_read: boolean; permissions: string[] | null;
  last_validated_at: string | null; created_at: string;
}
export interface BotSettingsOut {
  user_id: string; is_enabled: boolean; is_paused: boolean; risk_per_trade_pct: number;
  daily_loss_limit_pct: number; max_positions: number; max_leverage: number;
  reward_risk_ratio: number; trading_enabled: boolean; symbols: string[] | null;
}
export interface SignalOut {
  id: string; symbol: string; direction: string; timeframe: string;
  entry_price: number | null; stop_loss: number | null; take_profit: number | null;
  confidence_score: number | null; indicators: Record<string, unknown> | null;
  supporting_conditions: string[] | null; invalidating_conditions: string[] | null;
  status: string; created_at: string;
}
export interface TradeOut {
  id: string; symbol: string; side: string; status: string;
  entry_price: number | null; exit_price: number | null; quantity: number | null;
  leverage: number; realized_pnl: number | null; fees: number | null;
  environment: string; opened_at: string; closed_at: string | null;
}
export interface PositionOut {
  id: string; symbol: string; side: string; quantity: number; entry_price: number;
  mark_price: number | null; leverage: number; unrealized_pnl: number | null;
  liquidation_price: number | null; is_open: boolean;
}
export interface OrderOut {
  id: string; symbol: string; client_order_id: string; side: string; order_type: string;
  status: string; quantity: number; price: number | null; executed_qty: number;
  avg_price: number | null; reduce_only: boolean; created_at: string;
}
export interface NotificationOut { id: string; type: string; title: string; message: string; is_read: boolean; created_at: string; }
export interface DashboardOverview {
  user_id: string; open_positions: number; total_trades: number;
  total_realized_pnl: string; unread_notifications: number; latest_signals: SignalOut[];
  closed_trades: number; trading_volume: number; win_rate: number | null;
  max_drawdown: number; available_balance: number | null;
  available_balance_status: string;
}
export interface KlineOut {
  open_time: number; open: string; high: string; low: string; close: string;
  volume: string; close_time: number;
}
export interface AdminSignalRow {
  id: string; symbol: string; direction: string; timeframe: string;
  entry_price: string | null; stop_loss: string | null; take_profit: string | null;
  confidence_score: string | null; status: string; strategy_id: string | null; created_at: string;
}
export interface StrategyPerformanceRow {
  strategy_id: string | null; name: string; is_system: boolean; total_signals: number;
  signals_by_direction: Record<string, number>; total_trades: number; closed_trades: number;
  win_rate: number | null; realized_pnl: number;
}
export interface StrategiesPerformance {
  total_signals: number; signals_by_direction: Record<string, number>;
  total_trades: number; closed_trades: number; win_rate: number | null;
  realized_pnl: number; strategies: StrategyPerformanceRow[];
}
export interface HealthStatus { status: string; database: string; worker: string; exchange_reachable: boolean; testnet: boolean; }
export interface AdminOverview { total_users: number; active_bots: number; open_positions: number; total_trades: number; suspended_users: number; connected_binance_accounts: number; total_trading_volume: number; aggregate_realized_pnl: number; }
export interface AdminUserOut {
  id: string; email: string; full_name: string | null; is_active: boolean; is_suspended: boolean;
  is_email_verified: boolean; last_login_at: string | null; created_at: string;
}
export interface AdminTradeRow { id: string; user_id: string; symbol: string; side: string; status: string; entry_price: string; realized_pnl: string; opened_at: string; }
export interface AdminPositionRow { id: string; user_id: string; symbol: string; side: string; quantity: string; entry_price: string; }
export interface AuditLogOut { id: string; admin_id: string; action: string; target_type: string | null; target_id: string | null; details: Record<string, unknown> | null; created_at: string; }
export interface SystemHealth { database: string; exchange_reachable: boolean; environment: string; testnet: boolean; }

// ---------------------------------------------------------------- auth
export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    apiFetch<{ user: UserOut; verification_token: string; verification_url: string; note: string }>("/api/v1/auth/register", { method: "POST", body: { email, password, full_name: full_name || null }, noAuthRedirect: true }),
  login: (email: string, password: string, totp_code?: string) =>
    apiFetch<TokenResponse>("/api/v1/auth/login", { method: "POST", body: { email, password, totp_code: totp_code || null }, noAuthRedirect: true }),
  logout: () => apiFetch<{ detail: string }>("/api/v1/auth/logout", { method: "POST" }),
  refresh: (refresh_token: string) =>
    apiFetch<TokenResponse>("/api/v1/auth/refresh", { method: "POST", body: { refresh_token }, noAuthRedirect: true }),
  verifyEmail: (token: string) => apiFetch<{ detail: string }>("/api/v1/auth/verify-email", { method: "POST", body: { token }, noAuthRedirect: true }),
  forgotPassword: (email: string) =>
    apiFetch<{ detail: string; dev_reset_token?: string }>("/api/v1/auth/forgot-password", { method: "POST", body: { email }, noAuthRedirect: true }),
  resetPassword: (token: string, new_password: string) =>
    apiFetch<{ detail: string }>("/api/v1/auth/reset-password", { method: "POST", body: { token, new_password }, noAuthRedirect: true }),
  me: () => apiFetch<UserOut>("/api/v1/auth/me"),
  updateProfile: (full_name: string) =>
    apiFetch<UserOut>("/api/v1/auth/me", { method: "PUT", body: { full_name } }),
  changePassword: (current_password: string, new_password: string) =>
    apiFetch<{ detail: string }>("/api/v1/auth/change-password", { method: "POST", body: { current_password, new_password } }),
  twofaSetup: () =>
    apiFetch<{ otpauth_uri: string; secret: string; detail: string }>("/api/v1/auth/2fa/setup", { method: "POST" }),
  twofaVerify: (code: string) =>
    apiFetch<{ detail: string; totp_enabled: boolean }>("/api/v1/auth/2fa/verify", { method: "POST", body: { code } }),
  twofaDisable: (current_password: string, code?: string) =>
    apiFetch<{ detail: string; totp_enabled: boolean }>("/api/v1/auth/2fa/disable", { method: "POST", body: { current_password, code: code || null } }),
  sessions: () => apiFetch<SessionOut[]>("/api/v1/auth/sessions"),
  revokeSession: (id: string) => apiFetch<{ detail: string }>(`/api/v1/auth/sessions/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------- user
export const userApi = {
  health: () => apiFetch<HealthStatus>("/health", { noAuthRedirect: true }),
  klines: (symbol: string, interval = "1h", limit = 100) =>
    apiFetch<KlineOut[]>(`/api/v1/market/klines?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=${limit}`),
  contact: (name: string, email: string, message: string) =>
    apiFetch<{ id: string; name: string; email: string; message: string; created_at: string }>("/api/v1/contact", { method: "POST", body: { name, email, message }, noAuthRedirect: true }),
  overview: () => apiFetch<DashboardOverview>("/api/v1/dashboard/overview"),
  connections: () => apiFetch<ConnectionOut[]>("/api/v1/connections"),
  createConnection: (api_key: string, api_secret: string, environment: string, label?: string) =>
    apiFetch<ConnectionOut>("/api/v1/connections", { method: "POST", body: { api_key, api_secret, environment, label: label || null } }),
  validateConnection: (id: string) => apiFetch<ConnectionOut>(`/api/v1/connections/${id}/validate`, { method: "POST" }),
  deleteConnection: (id: string) => apiFetch<{ detail: string }>(`/api/v1/connections/${id}`, { method: "DELETE" }),
  botSettings: () => apiFetch<BotSettingsOut>("/api/v1/bot/settings"),
  updateBotSettings: (body: Partial<BotSettingsOut>) => apiFetch<BotSettingsOut>("/api/v1/bot/settings", { method: "PUT", body }),
  startBot: () => apiFetch<{ detail: string }>("/api/v1/bot/start", { method: "POST" }),
  stopBot: () => apiFetch<{ detail: string }>("/api/v1/bot/stop", { method: "POST" }),
  signals: (symbol?: string, limit = 50) =>
    apiFetch<SignalOut[]>(`/api/v1/signals?limit=${limit}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ""}`),
  trades: (limit = 50) => apiFetch<TradeOut[]>(`/api/v1/trades?limit=${limit}`),
  trade: (id: string) => apiFetch<TradeOut>(`/api/v1/trades/${id}`),
  positions: () => apiFetch<PositionOut[]>("/api/v1/positions"),
  orders: (limit = 50) => apiFetch<OrderOut[]>(`/api/v1/orders?limit=${limit}`),
  notifications: () => apiFetch<NotificationOut[]>("/api/v1/notifications"),
  markNotificationRead: (id: string) => apiFetch<{ detail: string }>(`/api/v1/notifications/${id}/read`, { method: "POST" }),
  scannerRun: (symbols?: string) => apiFetch<{ scanned: string[]; signals_generated: number; signals: { symbol: string; direction: string; timeframe: string }[] }>(`/api/v1/scanner/run${symbols ? `?symbols=${encodeURIComponent(symbols)}` : ""}`),
  scannerStatus: () => apiFetch<{ status: string; last_signal_at: string | null; default_symbols: string[] }>("/api/v1/scanner/status"),
};

// ---------------------------------------------------------------- admin
export const adminApi = {
  login: (email: string, password: string, totp_code?: string) =>
    apiFetch<{ access_token: string; token_type: string }>("/api/v1/admin/login", { method: "POST", body: { email, password, totp_code: totp_code || null }, noAuthRedirect: true, admin: true }),
  overview: () => apiFetch<AdminOverview>("/api/v1/admin/overview", { admin: true }),
  users: (search?: string, limit = 50) =>
    apiFetch<AdminUserOut[]>(`/api/v1/admin/users?limit=${limit}${search ? `&search=${encodeURIComponent(search)}` : ""}`, { admin: true }),
  user: (id: string) => apiFetch<AdminUserOut>(`/api/v1/admin/users/${id}`, { admin: true }),
  suspendUser: (id: string) => apiFetch<{ detail: string }>(`/api/v1/admin/users/${id}/suspend`, { method: "POST", admin: true }),
  reactivateUser: (id: string) => apiFetch<{ detail: string }>(`/api/v1/admin/users/${id}/reactivate`, { method: "POST", admin: true }),
  trades: (limit = 50) => apiFetch<AdminTradeRow[]>(`/api/v1/admin/trades?limit=${limit}`, { admin: true }),
  signals: (params?: { symbol?: string; direction?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.direction) q.set("direction", params.direction);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return apiFetch<{ total: number; limit: number; offset: number; signals: AdminSignalRow[] }>(`/api/v1/admin/signals${qs ? `?${qs}` : ""}`, { admin: true });
  },
  strategiesPerformance: () => apiFetch<StrategiesPerformance>("/api/v1/admin/strategies/performance", { admin: true }),
  positions: () => apiFetch<AdminPositionRow[]>("/api/v1/admin/positions", { admin: true }),
  pauseAllBots: () => apiFetch<{ detail: string }>("/api/v1/admin/bots/pause-all", { method: "POST", admin: true }),
  resumeAllBots: () => apiFetch<{ detail: string }>("/api/v1/admin/bots/resume-all", { method: "POST", admin: true }),
  pauseUserBot: (userId: string) => apiFetch<{ detail: string }>(`/api/v1/admin/bots/${userId}/pause`, { method: "POST", admin: true }),
  resumeUserBot: (userId: string) => apiFetch<{ detail: string }>(`/api/v1/admin/bots/${userId}/resume`, { method: "POST", admin: true }),
  auditLogs: (limit = 100) => apiFetch<AuditLogOut[]>(`/api/v1/admin/audit-logs?limit=${limit}`, { admin: true }),
  systemHealth: () => apiFetch<SystemHealth>("/api/v1/admin/system/health", { admin: true }),
  settings: () => apiFetch<Record<string, string>>("/api/v1/admin/settings", { admin: true }),
  updateSetting: (key: string, value: string) => apiFetch<{ key: string; value: string }>(`/api/v1/admin/settings/${key}`, { method: "PUT", body: { value }, admin: true }),
  maintenance: (enabled: boolean, message?: string) =>
    apiFetch<{ maintenance_mode: boolean }>("/api/v1/admin/maintenance", { method: "POST", body: { enabled, message: message || null }, admin: true }),
  activateLiveTrading: () =>
    apiFetch<{ detail: string; live_trading_enabled: boolean }>("/api/v1/admin/live-trading/activate", { method: "POST", body: { confirm: true, acknowledgement: "I understand live trading risks real money" }, admin: true }),
  deactivateLiveTrading: () =>
    apiFetch<{ detail: string; live_trading_enabled: boolean }>("/api/v1/admin/live-trading/deactivate", { method: "POST", admin: true }),
};

export { API_URL };
