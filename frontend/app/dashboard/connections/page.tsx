"use client";
import { useEffect, useState } from "react";
import { KeyRound, ShieldCheck, Trash2 } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Alert } from "@/components/ui/alert";
import { Skeleton, TableSkeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/dialog";
import { userApi, ApiError, type ConnectionOut } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function ConnectionsPage() {
  const [conns, setConns] = useState<ConnectionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [env, setEnv] = useState("production");
  const [label, setLabel] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError("");
    try { setConns(await userApi.connections()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load connections."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault(); setError(""); setNotice(""); setSaving(true);
    try {
      await userApi.createConnection(apiKey.trim(), apiSecret.trim(), env, label.trim() || undefined);
      setApiKey(""); setApiSecret(""); setLabel("");
      setNotice("Connection added. Run Validate to check it against Binance.");
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not add the connection."); }
    finally { setSaving(false); }
  };

  const validate = async (id: string) => {
    setBusyId(id); setError(""); setNotice("");
    try { await userApi.validateConnection(id); setNotice("Connection validated against Binance."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Validation failed."); }
    finally { setBusyId(null); }
  };

  const remove = async () => {
    if (!deleteId) return;
    setBusyId(deleteId); setError("");
    try { await userApi.deleteConnection(deleteId); setNotice("Connection deleted."); setDeleteId(null); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not delete the connection."); }
    finally { setBusyId(null); }
  };

  return (
    <div>
      <PageHeader title="Binance connections" description="Connect your Binance Futures API keys. Keys are encrypted at rest and shown masked." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Add a connection</CardTitle><CardDescription>Connect your live Binance Futures API key. Real money — the bot trades, but it can never withdraw funds.</CardDescription></CardHeader>
          <CardContent>
            <form onSubmit={add} className="space-y-4">
              <div className="space-y-2"><Label htmlFor="env">Environment</Label>
                <Select id="env" value={env} onChange={(e) => setEnv(e.target.value)}>
                  <option value="production">Live (real money — Binance Futures)</option>
                </Select>
              </div>
              <div className="space-y-2"><Label htmlFor="label">Label</Label><Input id="label" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Main Binance" /></div>
              <div className="space-y-2"><Label htmlFor="apiKey">API key</Label><Input id="apiKey" value={apiKey} onChange={(e) => setApiKey(e.target.value)} required minLength={8} autoComplete="off" placeholder="Paste your Binance API key" /></div>
              <div className="space-y-2"><Label htmlFor="apiSecret">API secret</Label><Input id="apiSecret" type="password" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} required minLength={8} autoComplete="off" placeholder="Paste your Binance API secret" /></div>
              <Alert variant="warning" title="Create the key correctly on Binance">
                On binance.com, create the API key with Futures trading ON and Withdrawals OFF. The bot can place trades but can never withdraw your funds — withdrawal permission is refused during validation. Use only money you can afford to lose; leveraged trading can lose your entire margin.
              </Alert>
              <Button type="submit" disabled={saving}>{saving ? "Adding…" : "Add connection"}</Button>
            </form>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Your connections</CardTitle><CardDescription>{loading ? "Loading…" : `${conns.length} connection${conns.length === 1 ? "" : "s"}`}</CardDescription></CardHeader>
          <CardContent>
            {loading ? <TableSkeleton /> : conns.length === 0 ? (
              <EmptyState title="No connections yet" description="Add your live Binance Futures API key to start. Until then the scanner and bot have no exchange account to trade on." />
            ) : (
              <div className="space-y-3">
                {conns.map((c) => (
                  <div key={c.id} className="rounded-lg border border-border bg-[#0D1424] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <KeyRound className="h-4 w-4 text-blue-400" />
                        <span className="font-medium text-white">{c.label || "Binance connection"}</span>
                        <Badge variant={c.environment === "testnet" ? "default" : "warning"}>{c.environment === "testnet" ? "Testnet" : "Live"}</Badge>
                        <Badge variant={c.is_active ? "success" : "secondary"}>{c.is_active ? "Active" : "Inactive"}</Badge>
                      </div>
                      <code className="text-xs text-muted">{c.api_key_masked}</code>
                    </div>
                    <p className="mt-2 text-xs text-muted">
                      Exchange: {c.exchange} · Can read: {c.can_read ? "yes" : "no"} · Can trade: {c.can_trade ? "yes" : "no"}
                      {c.permissions && c.permissions.length > 0 && <> · Permissions: {c.permissions.join(", ")}</>}
                      <br />Last validated: {fmtDate(c.last_validated_at)} · Added: {fmtDate(c.created_at)}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => validate(c.id)} disabled={busyId === c.id}>
                        <ShieldCheck className="h-4 w-4" /> {busyId === c.id ? "Validating…" : "Validate"}
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => setDeleteId(c.id)} disabled={busyId === c.id}>
                        <Trash2 className="h-4 w-4" /> Disconnect
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <Dialog open={deleteId !== null} onClose={() => setDeleteId(null)} title="Disconnect this connection?"
        description="The encrypted key will be deleted from AI TradePilot. This does not delete the key on Binance — revoke it there too if it was exposed.">
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
          <Button variant="destructive" onClick={remove} disabled={busyId !== null}>Disconnect</Button>
        </div>
      </Dialog>
    </div>
  );
}
