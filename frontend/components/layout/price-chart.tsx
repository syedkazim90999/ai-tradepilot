"use client";
import { useEffect, useRef } from "react";
import { CandlestickChart } from "lucide-react";

export interface Candle { time: string | number; open: number; high: number; low: number; close: number; }

/**
 * Price chart (lightweight-charts). Renders real candles only when `candles`
 * are supplied (loaded from GET /api/v1/market/klines by the calling page).
 * With no candles it shows a clearly-labelled empty state — no data is
 * ever simulated.
 */
export function PriceChart({ candles, symbol, entry, stopLoss, takeProfit }: {
  candles?: Candle[]; symbol?: string; entry?: number | null; stopLoss?: number | null; takeProfit?: number | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!candles || candles.length === 0 || !containerRef.current) return;
    let chart: ReturnType<typeof import("lightweight-charts").createChart> | null = null;
    let series: ReturnType<ReturnType<typeof import("lightweight-charts").createChart>["addCandlestickSeries"]> | null = null;
    let cancelled = false;
    (async () => {
      const { createChart, ColorType } = await import("lightweight-charts");
      if (cancelled || !containerRef.current) return;
      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth, height: 320,
        layout: { background: { type: ColorType.Solid, color: "#0D1424" }, textColor: "#94A3B8" },
        grid: { vertLines: { color: "#1E293B" }, horzLines: { color: "#1E293B" } },
        timeScale: { borderColor: "#1E293B" },
        rightPriceScale: { borderColor: "#1E293B" },
      });
      series = chart.addCandlestickSeries({ upColor: "#22C55E", downColor: "#EF4444", wickUpColor: "#22C55E", wickDownColor: "#EF4444", borderVisible: false });
      series.setData(candles.map((c) => ({ time: c.time as never, open: c.open, high: c.high, low: c.low, close: c.close })));
      if (entry) series.createPriceLine({ price: entry, color: "#3B82F6", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "Entry" });
      if (stopLoss) series.createPriceLine({ price: stopLoss, color: "#EF4444", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "SL" });
      if (takeProfit) series.createPriceLine({ price: takeProfit, color: "#22C55E", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "TP" });
      chart.timeScale().fitContent();
    })();
    const onResize = () => { if (chart && containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth }); };
    window.addEventListener("resize", onResize);
    return () => { cancelled = true; window.removeEventListener("resize", onResize); if (chart) chart.remove(); };
  }, [candles, entry, stopLoss, takeProfit]);

  if (!candles || candles.length === 0) {
    return (
      <div className="flex h-[320px] flex-col items-center justify-center rounded-xl border border-dashed border-border bg-[#0D1424] px-6 text-center">
        <CandlestickChart className="h-8 w-8 text-muted" />
        <h3 className="mt-3 font-semibold text-white">No chart data{symbol ? ` for ${symbol}` : ""}</h3>
        <p className="mt-1 max-w-md text-sm text-muted">
          No candles could be loaded from the market klines endpoint right now
          (the exchange may be unreachable). Run the scanner to see live signals
          with entry, stop-loss and take-profit levels below. No chart data is simulated.
        </p>
      </div>
    );
  }
  return <div ref={containerRef} className="w-full rounded-xl border border-border bg-[#0D1424]" />;
}
