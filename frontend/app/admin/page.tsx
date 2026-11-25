"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { PageHeader, StatCard } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { adminApi, userApi, ApiError, type AdminOverview, type HealthStatus } from "@/lib/api";
import { fmtUsd } from "@/lib/utils";

export default function AdminOverviewPage() {
  const [ov, setOv] = useState<AdminOverview | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    setError("");
    try {
      const [o, h] = await Promise.all([adminApi.overview(), userApi.health()]);
      setOv(o); setHealth(h);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not load admin overview."); }
    finally { setLoading(false); setRefreshing(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader title="Admin overview" description="Platform-wide metrics and system health."
        action={<Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing}><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh</Button>} />
      {error && <Alert variant="error" className="mb-6">{error} <button className="underline" onClick={() => load(true)}>Retry</button></Alert>}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3, 4, 5, 6, 7].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : ov ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Total users" value={String(ov.total_users)} sub="Registered accounts" />
          <StatCard title="Active bots" value={String(ov.active_bots)} sub="Bots currently enabled" />
          <StatCard title="Open positions" value={String(ov.open_positions)} sub="Across all users" />
          <StatCard title="Total trades" value={String(ov.total_trades)} sub="All trades on record" />
          <StatCard title="Suspended users" value={String(ov.suspended_users)} sub="Accounts currently suspended" />
          <StatCard title="Connected Binance accounts" value={String(ov.connected_binance_accounts)} sub="Active exchange connections" />
          <StatCard title="Total trading volume" value={fmtUsd(ov.total_trading_volume)} sub="Closed-trade notional" />
          <StatCard title="Aggregate realized P&L" value={fmtUsd(ov.aggregate_realized_pnl)} tone={ov.aggregate_realized_pnl > 0 ? "profit" : ov.aggregate_realized_pnl < 0 ? "loss" : "default"} sub="All closed trades" />
        </div>
      ) : null}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>System health</CardTitle><CardDescription>From the public health endpoint and the admin system check.</CardDescription></CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-24 w-full" /> : health ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-muted">Overall status</dt><dd><Badge variant={health.status === "ok" ? "success" : "warning"}>{health.status}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Database</dt><dd><Badge variant={health.database === "ok" ? "success" : "destructive"}>{health.database}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Background worker</dt><dd><Badge variant={health.worker === "ok" ? "success" : "destructive"}>{health.worker}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Exchange reachable</dt><dd><Badge variant={health.exchange_reachable ? "success" : "destructive"}>{health.exchange_reachable ? "yes" : "no"}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Environment</dt><dd className="font-medium text-white">{health.testnet ? "Binance Testnet" : "Production"}</dd></div>
              </dl>
            ) : <p className="text-sm text-muted">Health data unavailable.</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Quick actions</CardTitle><CardDescription>Common admin tasks.</CardDescription></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Link href="/admin/users"><Button variant="outline">Manage users</Button></Link>
            <Link href="/admin/bots"><Button variant="outline">Manage bots</Button></Link>
            <Link href="/admin/trades"><Button variant="outline">View all trades</Button></Link>
            <Link href="/admin/audit"><Button variant="outline">Audit logs</Button></Link>
            <Link href="/admin/system"><Button variant="outline">System &amp; maintenance</Button></Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
