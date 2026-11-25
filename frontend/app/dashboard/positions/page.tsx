"use client";
import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { userApi, ApiError, type PositionOut } from "@/lib/api";
import { fmtUsd, fmtNum } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

export default function PositionsPage() {
  const [positions, setPositions] = useState<PositionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    setError("");
    try { setPositions(await userApi.positions()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load positions."); }
    finally { setLoading(false); setRefreshing(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader title="Open positions" description="Positions currently open on your account, with mark price and unrealized P&L."
        action={<Button variant="outline" size="sm" onClick={() => load(true)} disabled={refreshing}><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh</Button>} />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <Card>
        <CardHeader><CardTitle>Open positions</CardTitle><CardDescription>Data is fetched from the backend on each refresh; mark prices update as the backend reconciles them.</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : positions.length === 0 ? (
            <EmptyState title="No open positions" description="You have no open positions right now. Open positions appear here once the bot (or a manual trade) opens one." />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Qty</TableHead>
                <TableHead>Entry</TableHead><TableHead>Mark</TableHead><TableHead>Lev</TableHead>
                <TableHead>Unrealized P&amp;L</TableHead><TableHead>Liq. price</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {positions.map((p) => (
                  <TableRow key={p.id}>
                    <td className="p-3 font-medium text-white">{p.symbol}</td>
                    <td className="p-3"><Badge variant={p.side === "LONG" ? "success" : "destructive"}>{p.side}</Badge></td>
                    <td className="p-3">{fmtNum(p.quantity)}</td>
                    <td className="p-3">{fmtNum(p.entry_price)}</td>
                    <td className="p-3">{fmtNum(p.mark_price)}</td>
                    <td className="p-3">{p.leverage}x</td>
                    <td className={`p-3 font-medium ${p.unrealized_pnl === null ? "" : p.unrealized_pnl > 0 ? "text-green-400" : p.unrealized_pnl < 0 ? "text-red-400" : ""}`}>{p.unrealized_pnl === null ? "—" : fmtUsd(p.unrealized_pnl)}</td>
                    <td className="p-3">{fmtNum(p.liquidation_price)}</td>
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
