"use client";
import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog } from "@/components/ui/dialog";
import { userApi, ApiError, type TradeOut } from "@/lib/api";
import { fmtUsd, fmtNum, fmtDate } from "@/lib/utils";

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<TradeOut | null>(null);

  useEffect(() => {
    userApi.trades(100)
      .then(setTrades)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load trades."))
      .finally(() => setLoading(false));
  }, []);

  const pnlTone = (v: number | null) => (v === null ? "" : v > 0 ? "text-green-400" : v < 0 ? "text-red-400" : "text-slate-300");

  return (
    <div>
      <PageHeader title="Trade history" description="Every trade on record for your account — wins and losses, with fees and duration." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <Card>
        <CardHeader><CardTitle>Trades</CardTitle><CardDescription>Click a row for the full detail. P&L shown is realized P&L after fees as recorded by the backend.</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : trades.length === 0 ? (
            <EmptyState title="No trades yet" description="Trades appear here once the bot executes its first order (or you place one). Until then there is nothing to report — and nothing is invented." />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Status</TableHead>
                <TableHead>Entry</TableHead><TableHead>Exit</TableHead><TableHead>Qty</TableHead>
                <TableHead>Lev</TableHead><TableHead>Fees</TableHead><TableHead>P&amp;L</TableHead><TableHead>Opened</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {trades.map((t) => (
                  <TableRow key={t.id} className="cursor-pointer" onClick={() => setSelected(t)}>
                    <td className="p-3 font-medium text-white">{t.symbol}</td>
                    <td className="p-3"><Badge variant={t.side === "BUY" || t.side === "LONG" ? "success" : "destructive"}>{t.side}</Badge></td>
                    <td className="p-3"><Badge variant="secondary">{t.status}</Badge></td>
                    <td className="p-3">{fmtNum(t.entry_price)}</td>
                    <td className="p-3">{fmtNum(t.exit_price)}</td>
                    <td className="p-3">{fmtNum(t.quantity)}</td>
                    <td className="p-3">{t.leverage}x</td>
                    <td className="p-3">{fmtUsd(t.fees)}</td>
                    <td className={`p-3 font-medium ${pnlTone(t.realized_pnl)}`}>{t.realized_pnl === null ? "—" : fmtUsd(t.realized_pnl)}</td>
                    <td className="p-3 text-muted">{fmtDate(t.opened_at)}</td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <Dialog open={selected !== null} onClose={() => setSelected(null)} title={selected ? `${selected.symbol} — ${selected.side}` : ""} description={selected ? `Trade ${selected.id}` : undefined}>
        {selected && (
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div><dt className="text-muted">Status</dt><dd className="font-medium text-white">{selected.status}</dd></div>
            <div><dt className="text-muted">Environment</dt><dd className="font-medium text-white">{selected.environment}</dd></div>
            <div><dt className="text-muted">Entry price</dt><dd className="font-medium text-white">{fmtNum(selected.entry_price)}</dd></div>
            <div><dt className="text-muted">Exit price</dt><dd className="font-medium text-white">{fmtNum(selected.exit_price)}</dd></div>
            <div><dt className="text-muted">Quantity</dt><dd className="font-medium text-white">{fmtNum(selected.quantity)}</dd></div>
            <div><dt className="text-muted">Leverage</dt><dd className="font-medium text-white">{selected.leverage}x</dd></div>
            <div><dt className="text-muted">Fees</dt><dd className="font-medium text-white">{fmtUsd(selected.fees)}</dd></div>
            <div><dt className="text-muted">Realized P&amp;L</dt><dd className={`font-medium ${pnlTone(selected.realized_pnl)}`}>{selected.realized_pnl === null ? "—" : fmtUsd(selected.realized_pnl)}</dd></div>
            <div><dt className="text-muted">Opened</dt><dd className="font-medium text-white">{fmtDate(selected.opened_at)}</dd></div>
            <div><dt className="text-muted">Closed</dt><dd className="font-medium text-white">{fmtDate(selected.closed_at)}</dd></div>
          </dl>
        )}
      </Dialog>
    </div>
  );
}
