"use client";
import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { TradeOut } from "@/lib/api";

/** Cumulative realized P&L from real closed trades. Empty state when no trades exist. */
export function PnlChart({ trades }: { trades: TradeOut[] }) {
  const data = useMemo(() => {
    const closed = [...trades].filter((t) => t.status === "closed" && t.realized_pnl !== null)
      .sort((a, b) => new Date(a.opened_at).getTime() - new Date(b.opened_at).getTime());
    let cum = 0;
    return closed.map((t, i) => {
      cum += Number(t.realized_pnl);
      return { name: `#${i + 1} ${t.symbol}`, pnl: Number(t.realized_pnl), cum: Math.round(cum * 100) / 100 };
    });
  }, [trades]);

  if (data.length === 0) {
    return <div className="flex h-[280px] items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted">No closed trades yet — the P&amp;L chart will appear after your first closed trade.</div>;
  }
  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} />
          <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} tickFormatter={(v: number) => `$${v}`} />
          <Tooltip contentStyle={{ background: "#121A2A", border: "1px solid #1E293B", borderRadius: 8, color: "#E2E8F0" }} formatter={(value, name) => [`$${Number(value).toFixed(2)}`, name === "pnl" ? "Trade P&L" : "Cumulative P&L"]} />
          <Bar dataKey="pnl" name="pnl">
            {data.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? "#22C55E" : "#EF4444"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
