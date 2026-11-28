import { PublicLayout } from "@/components/layout/public-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";

const STEPS = [
  { n: "1", t: "Create an account", d: "Register with your email and a password (minimum 8 characters). Verify your email via the link sent to you. You can optionally enable two-factor authentication in Settings." },
  { n: "2", t: "Connect Binance (live)", d: "Create a live API key on binance.com with Futures trading ON and withdrawals OFF — the bot can trade but can never withdraw funds. Add it under Dashboard → Connections; it is encrypted at rest and shown masked." },
  { n: "3", t: "Validate the connection", d: "Run Validate on the connection. AI TradePilot checks the key against Binance and refuses keys that carry withdrawal permission." },
  { n: "4", t: "Configure the bot", d: "Under Dashboard → Trading Bot, set your risk per trade, daily loss limit, max positions, max leverage (10–50x, default 20x), reward/risk ratio and the symbols to scan. A stop-loss is attached to every trade." },
  { n: "5", t: "Review signals", d: "Run the scanner or wait for scheduled scans. Each signal shows direction, entry, stop-loss, take-profit, confidence and the conditions that support or invalidate it." },
  { n: "6", t: "Start the bot — or trade manually", d: "Enable the bot to execute signals automatically within your limits, or keep it off and use signals as research. You can stop it instantly at any time." },
];

export default function HowItWorksPage() {
  return (
    <PublicLayout title="How it works" intro="From account to first automated trade in six steps — live trading on Binance Futures with real money.">
      <div className="space-y-4">
        {STEPS.map((s) => (
          <Card key={s.n}>
            <CardHeader><div className="flex items-center gap-3"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">{s.n}</span><CardTitle>{s.t}</CardTitle></div></CardHeader>
            <CardContent><CardDescription>{s.d}</CardDescription></CardContent>
          </Card>
        ))}
      </div>
      <Alert variant="warning" title="Before you start">
        AI TradePilot is a tool, not a guarantee. Signals can be wrong, markets can gap past stop-losses, and leveraged trading can lose more than your initial margin in extreme conditions. This is live trading with real money at risk — a 2% adverse move can liquidate a 50x position. Only use funds you can afford to lose.
      </Alert>
    </PublicLayout>
  );
}
