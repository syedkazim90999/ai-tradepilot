import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI TradePilot — AI-Powered Binance Futures Trading",
  description: "Rule-based AI-assisted automated trading on Binance Futures — live, with real money at risk. No guaranteed returns — trading involves substantial risk of loss.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-slate-200 antialiased">{children}</body>
    </html>
  );
}
