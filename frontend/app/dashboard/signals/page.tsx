"use client";
import { useEffect, useState } from "react";
import { Radar, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { PriceChart, type Candle } from "@/components/layout/price-chart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/dialog";
import { userApi, ApiError, type SignalOut } from "@/lib/api";
import { fmtNum, timeAgo, fmtDate } from "@/lib/utils";

export default function SignalsPage() {
  const [signals, setSignals] = useState<SignalOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<SignalOut | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [scanning, setScanning] = useState(false);
  const [scanInfo, setScanInfo] = useState<{ scanned: string[]; signals_generated: number } | null>(null);

  const load = async (symbol?: string) => {
    setLoading(true); setError("");
    try { setSignals(await userApi.signals(symbol || undefined)); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load signals."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!selected) { setCandles([]); return; }
    let cancelled = false;
    userApi.klines(selected.symbol, selected.timeframe, 100)
      .then((kl) => { if (!cancelled) setCandles(kl.map((k) => ({ time: Math.floor(k.open_time / 1000), open: parseFloat(k.open), high: parseFloat(k.high), low: parseFloat(k.low), close: parseFloat(k.close) }))); })
      .catch(() => { if (!cancelled) setCandles([]); });
    return () => { cancelled = true; };
  }, [selected]);

  const runScanner = async () => {
    setScanning(true); setError(""); setNotice("");
    try {
      const res = await userApi.scannerRun(filter.trim() ? filter.trim().toUpperCase() : undefined);
      setScanInfo({ scanned: res.scanned, signals_generated: res.signals_generated });
      setNotice(`Scanner finished: ${res.signals_generated} new signal(s) from ${res.scanned.join(", ")}.`);
      await load(filter.trim() ? filter.trim().toUpperCase() : undefined);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Scanner run failed."); }
    finally { setScanning(false); }
  };

  return (
    <div>
      <PageHeader title="Signals" description="Latest rule-based scanner signals with entry, stop-loss and take-profit."
        action={<Button onClick={runScanner} disabled={scanning}><Radar className="h-4 w-4" /> {scanning ? "Scanning…" : "Run scanner"}</Button>} />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      {scanInfo && <p className="mb-4 text-xs text-muted">Last scan: {scanInfo.scanned.join(", ")} — {scanInfo.signals_generated} signal(s) generated.</p>}
      <div className="mb-4 flex max-w-sm gap-2">
        <Input placeholder="Filter by symbol, e.g. BTCUSDT" value={filter} onChange={(e) => setFilter(e.target.value)} />
        <Button variant="outline" onClick={() => load(filter.trim() ? filter.trim().toUpperCase() : undefined)}>Filter</Button>
      </div>
      <Card>
        <CardHeader><CardTitle>Latest signals</CardTitle><CardDescription>Signals are rule-based (RSI, MACD, EMA, Bollinger Bands, ATR, VWAP) — not predictions, and not financial advice.</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : signals.length === 0 ? (
            <EmptyState title="No signals yet" description="Run the scanner to generate signals for the default symbols, or filter by a symbol first. Signals appear here as the scanner finds them." action={<Button onClick={runScanner} disabled={scanning}>{scanning ? "Scanning…" : "Run scanner now"}</Button>} />
          ) : (
            <div className="space-y-3">
              {signals.map((s) => (
                <button key={s.id} onClick={() => setSelected(s)} className="block w-full rounded-lg border border-border bg-[#0D1424] p-4 text-left transition-colors hover:border-blue-500/50">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={s.direction === "LONG" ? "success" : s.direction === "SHORT" ? "destructive" : "secondary"}>{s.direction}</Badge>
                      <span className="font-semibold text-white">{s.symbol}</span>
                      <span className="text-xs text-muted">{s.timeframe}</span>
                      <Badge variant="secondary">{s.status}</Badge>
                      {s.direction === "LONG" ? <ArrowUpRight className="h-4 w-4 text-green-400" /> : s.direction === "SHORT" ? <ArrowDownRight className="h-4 w-4 text-red-400" /> : null}
                    </div>
                    <span className="text-xs text-muted">{timeAgo(s.created_at)}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-4 text-sm">
                    <span className="text-muted">Entry <span className="text-white">{fmtNum(s.entry_price)}</span></span>
                    <span className="text-muted">Stop-loss <span className="text-red-300">{fmtNum(s.stop_loss)}</span></span>
                    <span className="text-muted">Take-profit <span className="text-green-300">{fmtNum(s.take_profit)}</span></span>
                    {s.confidence_score !== null && <span className="text-muted">Confidence <span className="text-white">{fmtNum(s.confidence_score, 2)}</span></span>}
                    <span className="text-blue-400">View details →</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <Dialog open={selected !== null} onClose={() => setSelected(null)} title={selected ? `${selected.symbol} — ${selected.direction}` : ""} description={selected ? `${selected.timeframe} · ${fmtDate(selected.created_at)} · status: ${selected.status}` : undefined}>
        {selected && (
          <div className="space-y-4">
            <PriceChart candles={candles} symbol={selected.symbol} entry={selected.entry_price ? Number(selected.entry_price) : null} stopLoss={selected.stop_loss ? Number(selected.stop_loss) : null} takeProfit={selected.take_profit ? Number(selected.take_profit) : null} />
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <div><dt className="text-muted">Entry</dt><dd className="font-medium text-white">{fmtNum(selected.entry_price)}</dd></div>
              <div><dt className="text-muted">Stop-loss</dt><dd className="font-medium text-red-300">{fmtNum(selected.stop_loss)}</dd></div>
              <div><dt className="text-muted">Take-profit</dt><dd className="font-medium text-green-300">{fmtNum(selected.take_profit)}</dd></div>
              <div><dt className="text-muted">Confidence</dt><dd className="font-medium text-white">{selected.confidence_score !== null ? fmtNum(selected.confidence_score, 2) : "—"}</dd></div>
            </dl>
            {selected.supporting_conditions && selected.supporting_conditions.length > 0 && (
              <div><h4 className="text-sm font-semibold text-green-300">Supporting conditions</h4><ul className="mt-1 list-disc pl-5 text-sm text-slate-300">{selected.supporting_conditions.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
            )}
            {selected.invalidating_conditions && selected.invalidating_conditions.length > 0 && (
              <div><h4 className="text-sm font-semibold text-red-300">Invalidating conditions</h4><ul className="mt-1 list-disc pl-5 text-sm text-slate-300">{selected.invalidating_conditions.map((c, i) => <li key={i}>{c}</li>)}</ul></div>
            )}
            {selected.indicators && (
              <div><h4 className="text-sm font-semibold text-white">Indicator snapshot</h4>
                <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-[#0D1424] p-3 text-xs text-slate-300">{JSON.stringify(selected.indicators, null, 2)}</pre></div>
            )}
          </div>
        )}
      </Dialog>
    </div>
  );
}
