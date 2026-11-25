"use client";
import { useEffect, useState } from "react";
import { Bot, Pause, Play } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog } from "@/components/ui/dialog";
import { adminApi, userApi, ApiError, type AdminPositionRow } from "@/lib/api";

export default function AdminBotsPage() {
  const [positions, setPositions] = useState<AdminPositionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<"pause-all" | "resume-all" | null>(null);

  const load = async () => {
    setLoading(true); setError("");
    try { setPositions(await adminApi.positions()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load open positions."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const doGlobal = async () => {
    if (!confirm) return;
    setBusy(true); setError("");
    try {
      const res = confirm === "pause-all" ? await adminApi.pauseAllBots() : await adminApi.resumeAllBots();
      setNotice(res.detail); setConfirm(null);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Action failed."); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="Bots" description="Global and per-user bot controls, plus all open positions." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Global controls</CardTitle><CardDescription>Pause or resume every user bot at once. Audit-logged.</CardDescription></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button variant="destructive" onClick={() => setConfirm("pause-all")}><Pause className="h-4 w-4" /> Pause all bots</Button>
            <Button variant="success" onClick={() => setConfirm("resume-all")}><Play className="h-4 w-4" /> Resume all bots</Button>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Per-user controls</CardTitle><CardDescription>Pause or resume one user&rsquo;s bot from their detail page.</CardDescription></CardHeader>
          <CardContent>
            <p className="text-sm text-muted">Open <a className="text-blue-400 underline" href="/admin/users">Users</a>, choose a user, and use &ldquo;Pause user bot&rdquo; / &ldquo;Resume user bot&rdquo; on their detail page. A paused user cannot start their bot until the pause is lifted.</p>
            <Alert className="mt-4" title="Signal history & strategy performance">
              The API does not expose admin signal history or per-strategy performance endpoints yet, so those views are not available here. User-level signals are visible to each user under Dashboard → Signals.
            </Alert>
          </CardContent>
        </Card>
      </div>
      <Card className="mt-4">
        <CardHeader><CardTitle>All open positions</CardTitle><CardDescription>{loading ? "Loading…" : `${positions.length} open position(s) across all users`}</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : positions.length === 0 ? (
            <EmptyState title="No open positions" description="No user currently has an open position." />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Symbol</TableHead><TableHead>Side</TableHead><TableHead>Quantity</TableHead><TableHead>Entry</TableHead><TableHead>User ID</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {positions.map((p) => (
                  <TableRow key={p.id}>
                    <td className="p-3 font-medium text-white">{p.symbol}</td>
                    <td className="p-3"><Badge variant={p.side === "LONG" ? "success" : "destructive"}>{p.side}</Badge></td>
                    <td className="p-3">{p.quantity}</td>
                    <td className="p-3">{p.entry_price}</td>
                    <td className="p-3 font-mono text-xs text-muted">{p.user_id.slice(0, 8)}…</td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <Dialog open={confirm !== null} onClose={() => setConfirm(null)}
        title={confirm === "pause-all" ? "Pause ALL user bots?" : "Resume ALL user bots?"}
        description={confirm === "pause-all"
          ? "Every user bot will be paused and no new trades will be placed until resumed. Use this for emergencies or maintenance."
          : "Every paused user bot will be resumed. Users can then start their bots again."}>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setConfirm(null)}>Cancel</Button>
          <Button variant={confirm === "pause-all" ? "destructive" : "success"} onClick={doGlobal} disabled={busy}>
            <Bot className="h-4 w-4" /> {busy ? "Working…" : confirm === "pause-all" ? "Pause all bots" : "Resume all bots"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
