"use client";
import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/dialog";
import { adminApi, userApi, ApiError, type SystemHealth, type HealthStatus } from "@/lib/api";

export default function AdminSystemPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [publicHealth, setPublicHealth] = useState<HealthStatus | null>(null);
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [liveConfirm, setLiveConfirm] = useState(false);
  const [livePhrase, setLivePhrase] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const [h, ph, s] = await Promise.all([adminApi.systemHealth(), userApi.health(), adminApi.settings()]);
      setHealth(h); setPublicHealth(ph); setSettings(s);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not load system status."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const toggleMaintenance = async (enabled: boolean) => {
    setBusy(true); setError(""); setNotice("");
    try {
      await adminApi.maintenance(enabled);
      setNotice(enabled ? "Maintenance mode enabled." : "Maintenance mode disabled.");
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not change maintenance mode."); }
    finally { setBusy(false); }
  };

  const setSetting = async (key: string, value: string) => {
    setBusy(true); setError(""); setNotice("");
    try {
      await adminApi.updateSetting(key, value);
      setNotice(`Setting ${key} updated to ${value}.`);
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not update setting."); }
    finally { setBusy(false); }
  };

  const activateLive = async () => {
    if (livePhrase.trim() !== "I understand live trading risks real money") {
      setError("Type the exact acknowledgement phrase to activate live trading.");
      return;
    }
    setBusy(true); setError("");
    try {
      await adminApi.activateLiveTrading();
      setNotice("Live trading ENABLED — real money is now at risk.");
      setLiveConfirm(false); setLivePhrase("");
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not activate live trading."); }
    finally { setBusy(false); }
  };

  const deactivateLive = async () => {
    setBusy(true); setError("");
    try { await adminApi.deactivateLiveTrading(); setNotice("Live trading DISABLED."); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not deactivate live trading."); }
    finally { setBusy(false); }
  };

  const maintenance = settings["maintenance_mode"] === "true";
  const liveEnabled = settings["live_trading_enabled"] === "true";
  const emergencyStop = settings["emergency_stop"] === "true";

  return (
    <div>
      <PageHeader title="System" description="Health, worker status, settings and maintenance mode." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Health &amp; worker</CardTitle><CardDescription>Live status from the API.</CardDescription></CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-32 w-full" /> : (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-muted">Database</dt><dd><Badge variant={health?.database === "ok" ? "success" : "destructive"}>{health?.database ?? "unknown"}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Exchange reachable</dt><dd><Badge variant={health?.exchange_reachable ? "success" : "destructive"}>{health?.exchange_reachable ? "yes" : "no"}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Background worker</dt><dd><Badge variant={publicHealth?.worker === "ok" ? "success" : "destructive"}>{publicHealth?.worker ?? "unknown"}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Overall status</dt><dd><Badge variant={publicHealth?.status === "ok" ? "success" : "warning"}>{publicHealth?.status ?? "unknown"}</Badge></dd></div>
                <div className="flex justify-between"><dt className="text-muted">Environment</dt><dd className="font-medium text-white">{health?.environment ?? "—"}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Binance mode</dt><dd><Badge variant={health?.testnet ? "default" : "warning"}>{health?.testnet ? "Testnet" : "Production"}</Badge></dd></div>
              </dl>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Maintenance mode</CardTitle><CardDescription>When enabled, the platform is in maintenance.</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted">Maintenance mode</span>
              <Switch checked={maintenance} onCheckedChange={toggleMaintenance} disabled={busy} label="Maintenance mode" />
            </div>
            <p className="text-xs text-muted">Current value: <code>{settings["maintenance_mode"] ?? "not set"}</code></p>
            <div className="flex items-center justify-between border-t border-border pt-3">
              <span className="text-sm text-muted">Emergency stop (no new trades)</span>
              <Switch checked={emergencyStop} onCheckedChange={(v) => setSetting("emergency_stop", String(v).toLowerCase())} disabled={busy} label="Emergency stop" />
            </div>
            <p className="text-xs text-muted">Current value: <code>{settings["emergency_stop"] ?? "not set"}</code></p>
          </CardContent>
        </Card>
      </div>
      <Card className="mt-4 border-red-500/40">
        <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-red-400" /> Live trading activation</CardTitle>
          <CardDescription>Danger zone. Production trading is disabled by default for a reason.</CardDescription></CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted">Live trading is currently <strong className={liveEnabled ? "text-red-300" : "text-green-300"}>{liveEnabled ? "ENABLED — real money is at risk" : "DISABLED"}</strong>.</p>
          {liveEnabled ? (
            <Button variant="destructive" onClick={deactivateLive} disabled={busy}>Disable live trading</Button>
          ) : (
            <Button variant="destructive" onClick={() => setLiveConfirm(true)}>Activate live trading…</Button>
          )}
        </CardContent>
      </Card>
      <Dialog open={liveConfirm} onClose={() => setLiveConfirm(false)} title="Activate live trading?"
        description="This enables production trading with real money. You must type the exact acknowledgement phrase. This action is audit-logged.">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="phrase">Type: I understand live trading risks real money</Label>
            <Input id="phrase" value={livePhrase} onChange={(e) => setLivePhrase(e.target.value)} placeholder="I understand live trading risks real money" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setLiveConfirm(false)}>Cancel</Button>
            <Button variant="destructive" onClick={activateLive} disabled={busy}>Activate live trading</Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
