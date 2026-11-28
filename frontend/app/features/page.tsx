import { BarChart3, Bot, KeyRound, Radar, ShieldCheck, Wallet } from "lucide-react";
import { PublicLayout } from "@/components/layout/public-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  { icon: Radar, title: "Market scanner", text: "Continuously scans Binance Futures symbols using RSI, MACD, EMA 20/50/200, Bollinger Bands, ATR and VWAP. Signals are deterministic and rule-based — no black-box model decides for you." },
  { icon: Bot, title: "Automated execution", text: "When a signal passes your filters, the bot places the order with your configured leverage, position size, stop-loss and take-profit. You can pause it at any time." },
  { icon: ShieldCheck, title: "Risk management", text: "Conservative defaults: 0.5% risk per trade, 2% daily loss limit, max 2 positions, leverage 10–50x and a 2:1 reward/risk target. A stop-loss is attached to every trade. A global emergency stop halts all new trades." },
  { icon: KeyRound, title: "Encrypted connections", text: "Binance API keys are encrypted with Fernet before storage. Only the last 4 characters are ever displayed, and keys with withdrawal permission are refused during validation." },
  { icon: BarChart3, title: "Analytics & history", text: "Realized P&L, trade history, open positions, orders and signal history — computed from your own account activity, never fabricated." },
  { icon: Wallet, title: "Testnet first", text: "The platform defaults to Binance Futures Testnet. Production trading is disabled by default and needs an explicit Super Admin activation." },
];

export default function FeaturesPage() {
  return (
    <PublicLayout title="Features" intro="Everything AI TradePilot does — and the limits it respects.">
      <div className="grid gap-4 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <Card key={f.title}>
            <CardHeader><f.icon className="h-6 w-6 text-blue-400" /><CardTitle className="mt-2">{f.title}</CardTitle></CardHeader>
            <CardContent><CardDescription>{f.text}</CardDescription></CardContent>
          </Card>
        ))}
      </div>
      <p className="text-sm text-muted">Signals are rule-based today; no machine-learning confirmation model is wired in yet. The scanner reports what it computed and why — check the signal detail before enabling auto-trading.</p>
    </PublicLayout>
  );
}
