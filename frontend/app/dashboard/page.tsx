"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowUpRight, ArrowDownRight, RefreshCw } from "lucide-react";
import { PageHeader, StatCard } from "@/components/layout/shared";
import { PriceChart } from "@/components/layout/price-chart";import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { userApi, ApiError, type DashboardOverview, type TradeOut } from "@/lib/api";
import type { Candle } from "@/components/layout/price-chart";
import { fmtUsd, fmtNum, timeAgo } from "@/lib/utils";
import dynamic from "next/dynamic";

const PnlChart = dynamic(() => import("@/components/layout/pnl-chart").then((m) => m.PnlChart), { ssr: false, loading: () => <Skeleton className="h-[280px] w-full" /> });

export default function DashboardOverviewPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [trades, setTrades] = useState<TradeOut[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    setError("");
    try {
      const [ov, tr] = await Promise.all([userApi.overview(), userApi.trades(50)]);
      setData(ov); setTrades(tr);
      const sym = ov.latest_signals?.[0]?.symbol;
      if (sym) {
        try {
          const kl = await userApi.klines(sym, "1h", 100);
          setCandles(kl.map((k) => ({ time: Math.floor(k.open_time / 1000), open: parseFloat(k.open), high: parseFloat(k.high), low: parseFloat(k.low), close: parseFloat(k.close) })));
        } catch { setCandles([]); }
      } else setCandles([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load the dashboard. Please try again.");
    } finally { setLoading(false); setRefreshing(false); }
  };
  useEffect(() => { load(); }, []);

  const pnl = data ? parseFloat(data.total_realized_pnl) : 0;

  return (
    <div>
      <PageHeader title="Overview" description="Your account, bot and trading activity — live from the API."
        action={<Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing}><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh</Button>} />
      {error && <Alert variant="error" className="mb-6">{error} <button className="underline" onClick={() => load(true)}>Retry</button></Alert>}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Realized P&L (all time)" value={fmtUsd(pnl)} tone={pnl > 0 ? "profit" : pnl < 0 ? "loss" : "default"} sub={`${data.total_trades} closed trades`} />
            <StatCard title="Open positions" value={String(data.open_positions)} sub="From your Binance connection" />
            <StatCard title="Total trades" value={String(data.total_trades)} sub="All trades on record" />
            <StatCard title="Unread notifications" value={String(data.unread_notifications)} sub="See Notifications for details" />
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Win rate" value={data.win_rate === null ? "—" : `${(data.win_rate * 100).toFixed(1)}%`} sub={`${data.closed_trades} closed trades`} />
            <StatCard title="Trading volume" value={fmtUsd(data.trading_volume)} sub="Closed-trade notional" />
            <StatCard title="Max drawdown" value={fmtUsd(data.max_drawdown)} sub="From closed-trade P&L curve" />
            <StatCard title="Available balance (USDT)" value={data.available_balance === null ? "—" : fmtUsd(data.available_balance)} sub={data.available_balance_status === "no_binance_connection" ? "No Binance account connected" : data.available_balance_status === "fetch_failed" ? "Balance fetch failed" : "From your Binance account"} />
          </div>
        </>
      ) : null}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Price chart</CardTitle><CardDescription>Live candles from Binance Futures for {data?.latest_signals?.[0]?.symbol || "your latest signal"}.</CardDescription></CardHeader>
          <CardContent><PriceChart candles={candles} symbol={data?.latest_signals?.[0]?.symbol} entry={data?.latest_signals?.[0]?.entry_price ? Number(data.latest_signals[0].entry_price) : null} stopLoss={data?.latest_signals?.[0]?.stop_loss ? Number(data.latest_signals[0].stop_loss) : null} takeProfit={data?.latest_signals?.[0]?.take_profit ? Number(data.latest_signals[0].take_profit) : null} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Cumulative realized P&L</CardTitle><CardDescription>Built from your actual closed trades (oldest → newest).</CardDescription></CardHeader>
          <CardContent>{loading ? <Skeleton className="h-[280px] w-full" /> : <PnlChart trades={trades} />}</CardContent>
        </Card>
      </div>
      <Card className="mt-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <div><CardTitle>Latest signals</CardTitle><CardDescription>Most recent scanner signals.</CardDescription></div>
          <Link href="/dashboard/signals"><Button variant="outline" size="sm">All signals</Button></Link>
        </CardHeader>
        <CardContent>
          {loading ? <Skeleton className="h-24 w-full" /> : data && data.latest_signals.length === 0 ? (
            <p className="text-sm text-muted">No signals yet. Run the scanner from the Signals page.</p>
          ) : (
            <div className="space-y-3">
              {data?.latest_signals.map((s) => (
                <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-[#0D1424] px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={s.direction === "LONG" ? "success" : s.direction === "SHORT" ? "destructive" : "secondary"}>{s.direction}</Badge>
                    <span className="font-medium text-white">{s.symbol}</span>
                    <span className="text-xs text-muted">{s.timeframe} · {timeAgo(s.created_at)}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <span className="text-muted">Entry <span className="text-white">{fmtNum(s.entry_price)}</span></span>
                    {s.confidence_score !== null && <span className="text-muted">Confidence <span className="text-white">{fmtNum(s.confidence_score, 2)}</span></span>}
                    {s.direction === "LONG" ? <ArrowUpRight className="h-4 w-4 text-green-400" /> : s.direction === "SHORT" ? <ArrowDownRight className="h-4 w-4 text-red-400" /> : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
