"use client";
import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { adminApi, ApiError, type AdminTradeRow } from "@/lib/api";
import { fmtUsd, fmtDate } from "@/lib/utils";

export default function AdminTradesPage() {
  const [trades, setTrades] = useState<AdminTradeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState("");
  const [userFilter, setUserFilter] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try { setTrades(await adminApi.trades(100)); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load trades."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  // The admin trades endpoint supports only a limit query; symbol/side/user
  // filtering is applied client-side and labelled as such.
  const filtered = trades.filter((t) =>
    (!symbol || t.symbol.toUpperCase().includes(symbol.trim().toUpperCase())) &&
    (!side || t.side === side) &&
    (!userFilter || t.user_id.toLowerCase().includes(userFilter.trim().toLowerCase()))
  );

  return (
    <div>
      <PageHeader title="All trades" description="Every trade across all users, newest first." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <div className="mb-4 flex flex-wrap gap-2">
        <Input className="max-w-xs" placeholder="Filter by symbol, e.g. BTCUSDT" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
        <Select className="max-w-[180px]" value={side} onChange={(e) => setSide(e.target.value)}>
          <option value="">All sides</option><option value="BUY">BUY</option><option value="SELL">SELL</option><option value="LONG">LONG</option><option value="SHORT">SHORT</option>
        </Select>
        <Input className="max-w-xs" placeholder="Filter by user ID" value={userFilter} onChange={(e) => setUserFilter(e.target.value)} />
        <Button variant="outline" onClick={() => { setSymbol(""); setSide(""); setUserFilter(""); }}>Clear</Button>
      </div>
      <p className="mb-4 text-xs text-muted">Note: the admin trades API returns the latest trades only (limit-based); date filtering is not supported by the endpoint, so filters above apply to the loaded rows.</p>
      <Card>
        <CardHeader><CardTitle>Trades</CardTitle><CardDescription>{loading ? "Loading…" : `${filtered.length} of ${trades.length} loaded trade(s)`}</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : filtered.length === 0 ? (
            <EmptyState title="No trades match" description="No trades on record, or none match the current filters." />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Status</TableHead>
                <TableHead>Entry</TableHead><TableHead>Realized P&amp;L</TableHead><TableHead>User ID</TableHead><TableHead>Opened</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {filtered.map((t) => (
                  <TableRow key={t.id}>
                    <td className="p-3 font-medium text-white">{t.symbol}</td>
                    <td className="p-3"><Badge variant={t.side === "BUY" || t.side === "LONG" ? "success" : "destructive"}>{t.side}</Badge></td>
                    <td className="p-3"><Badge variant="secondary">{t.status}</Badge></td>
                    <td className="p-3">{t.entry_price}</td>
                    <td className={`p-3 font-medium ${parseFloat(t.realized_pnl) > 0 ? "text-green-400" : parseFloat(t.realized_pnl) < 0 ? "text-red-400" : ""}`}>{fmtUsd(t.realized_pnl)}</td>
                    <td className="p-3 font-mono text-xs text-muted">{t.user_id.slice(0, 8)}…</td>
                    <td className="p-3 text-muted">{fmtDate(t.opened_at)}</td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
