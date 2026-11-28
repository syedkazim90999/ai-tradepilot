"use client";
import { useEffect, useState } from "react";
import { Bot, Pause, Play } from "lucide-react";
import { PageHeader } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { userApi, ApiError, type BotSettingsOut } from "@/lib/api";

const DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"];

export default function BotPage() {
  const [s, setS] = useState<BotSettingsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [symbolsText, setSymbolsText] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const data = await userApi.botSettings();
      setS(data); setSymbolsText((data.symbols || []).join(", "));
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not load bot settings."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault(); if (!s) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const symbols = symbolsText.split(",").map((x) => x.trim().toUpperCase()).filter(Boolean);
      const updated = await userApi.updateBotSettings({ ...s, symbols });
      setS(updated); setNotice("Bot settings saved.");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not save settings."); }
    finally { setSaving(false); }
  };

  const toggle = async () => {
    if (!s) return;
    setToggling(true); setError(""); setNotice("");
    try {
      if (s.is_enabled) { await userApi.stopBot(); setNotice("Bot stopped. No new trades will be placed."); }
      else { await userApi.startBot(); setNotice("Bot started."); }
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not change bot state."); }
    finally { setToggling(false); }
  };

  const set = <K extends keyof BotSettingsOut>(k: K, v: BotSettingsOut[K]) => setS((prev) => (prev ? { ...prev, [k]: v } : prev));

  return (
    <div>
      <PageHeader title="Trading bot" description="Configure risk limits and execution. Trading is live with real money — a 2% adverse move can liquidate a 50x position."
        action={s ? (
          <Button variant={s.is_enabled ? "destructive" : "success"} onClick={toggle} disabled={toggling || s.is_paused}>
            {s.is_enabled ? <><Pause className="h-4 w-4" /> Stop bot</> : <><Play className="h-4 w-4" /> Start bot</>}
          </Button>
        ) : undefined} />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      {s?.is_paused && <Alert variant="warning" className="mb-4" title="Paused by admin">An admin has paused your bot. You cannot start it until the pause is lifted.</Alert>}
      {loading || !s ? (
        <div className="space-y-4"><Skeleton className="h-24 w-full" /><Skeleton className="h-64 w-full" /></div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader><CardTitle>Status</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2"><Bot className="h-5 w-5 text-blue-400" />
                <Badge variant={s.is_paused ? "warning" : s.is_enabled ? "success" : "secondary"}>
                  {s.is_paused ? "Paused by admin" : s.is_enabled ? "Running" : "Stopped"}
                </Badge>
              </div>
              <div className="flex items-center justify-between"><span className="text-sm text-muted">Auto-trading enabled</span>
                <Switch checked={s.trading_enabled} onCheckedChange={(v) => set("trading_enabled", v)} label="Auto-trading" /></div>
              <p className="text-xs leading-relaxed text-muted">
                When auto-trading is off, the bot still scans and records signals but places no orders.
                The scanner only ever generates rule-based signals — no model places orders on your behalf.
              </p>
              <div className="rounded-lg border border-border bg-[#0D1424] p-3 text-xs leading-relaxed text-muted">
                Defaults: 0.5% risk/trade · minimum $2 risk per trade · max 5 positions · leverage 10–50x (default 20x) · 2:1 reward/risk. A stop-loss is attached to every trade — there is no daily loss halt, the bot keeps trading.
              </div>
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Risk &amp; execution settings</CardTitle><CardDescription>Changes apply to future trades only.</CardDescription></CardHeader>
            <CardContent>
              <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2"><Label htmlFor="risk">Risk per trade (%)</Label><Input id="risk" type="number" step="0.1" min="0.1" max="5" value={Number(s.risk_per_trade_pct)} onChange={(e) => set("risk_per_trade_pct", Number(e.target.value))} /></div>
                <div className="space-y-2"><Label htmlFor="minrisk">Minimum risk per trade ($)</Label><Input id="minrisk" type="number" step="0.5" min="0" value={Number(s.min_risk_usd)} onChange={(e) => set("min_risk_usd", Number(e.target.value))} /><p className="text-xs text-muted">Never less than this per trade — the risk scales up from $2 as the account grows.</p></div>
                <div className="space-y-2"><Label htmlFor="daily">Daily loss limit (%)</Label><Input id="daily" type="number" step="0.1" min="0.5" max="20" value={Number(s.daily_loss_limit_pct)} onChange={(e) => set("daily_loss_limit_pct", Number(e.target.value))} /></div>
                <div className="space-y-2"><Label htmlFor="maxpos">Max positions (1–10)</Label><Input id="maxpos" type="number" min={1} max={10} value={s.max_positions} onChange={(e) => set("max_positions", Number(e.target.value))} /></div>
                <div className="space-y-2"><Label htmlFor="lev">Max leverage (10–50x)</Label><Input id="lev" type="number" min={10} max={50} value={s.max_leverage} onChange={(e) => set("max_leverage", Number(e.target.value))} /></div>
                <div className="space-y-2"><Label htmlFor="rr">Reward / risk ratio</Label><Input id="rr" type="number" step="0.1" min="0.5" max="5" value={Number(s.reward_risk_ratio)} onChange={(e) => set("reward_risk_ratio", Number(e.target.value))} /></div>
                <div className="space-y-2"><Label htmlFor="symbols">Symbols (comma-separated)</Label><Input id="symbols" value={symbolsText} onChange={(e) => setSymbolsText(e.target.value)} placeholder="BTCUSDT, ETHUSDT" /></div>
                <div className="sm:col-span-2 flex flex-wrap gap-2">
                  {DEFAULT_SYMBOLS.map((sym) => (
                    <Button key={sym} type="button" size="sm" variant="outline" onClick={() => setSymbolsText((t) => (t ? `${t}, ${sym}` : sym))}>{sym}</Button>
                  ))}
                </div>
                <div className="sm:col-span-2"><Button type="submit" disabled={saving}>{saving ? "Saving…" : "Save settings"}</Button></div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
