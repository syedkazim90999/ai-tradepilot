import { PublicLayout } from "@/components/layout/public-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FAQS = [
  { q: "What is AI TradePilot?", a: "An AI-assisted automated trading platform for Binance Futures. It scans the market with technical indicators, generates rule-based signals, and can execute trades automatically within risk limits you set." },
  { q: "Is my money at risk?", a: "On Testnet, no — you trade with test funds that have no real value. Production (live) trading is disabled by default and requires an explicit Super Admin activation with a written risk acknowledgement. Even then, all trading risks real loss." },
  { q: "Does AI TradePilot guarantee profits?", a: "No, and no honest trading service can. Signals are deterministic rules, not predictions. Markets can move against any position, and leveraged trading can lose money quickly." },
  { q: "How are my Binance API keys stored?", a: "They are encrypted with Fernet before being stored in the database. The dashboard only ever shows the last 4 characters of your key. Keys with withdrawal permission are refused during validation." },
  { q: "What happens if the bot loses money?", a: "Losses are limited by your configuration: risk per trade, daily loss limit, max positions and leverage caps. A daily loss limit stops new trades for the day, and you can pause the bot at any time." },
  { q: "Can I use my own strategy?", a: "Today the scanner uses a fixed set of indicators (RSI, MACD, EMA, Bollinger Bands, ATR, VWAP) with configurable risk parameters. Custom strategies are not yet supported." },
  { q: "What plans are available?", a: "Free ($0), Basic ($19/mo), Pro ($49/mo) and Premium ($99/mo). The Free plan includes the scanner but not auto-trading. Paid checkout is coming soon — registering now gives you the Free plan." },
  { q: "How do I cancel or delete my account?", a: "You can stop the bot and disconnect Binance at any time from the dashboard. For account deletion, contact support from your registered email." },
  { q: "Is AI TradePilot financial advice?", a: "No. Signals and automation are tools, not advice. You are responsible for your own trading decisions and for understanding the risks." },
  { q: "Which markets does it trade?", a: "Binance Futures (USDT-margined perpetuals) on the symbols you configure, starting with the scanner's default symbol set." },
];

export default function FaqPage() {
  return (
    <PublicLayout title="Frequently asked questions" intro="Straight answers — including the uncomfortable ones about risk.">
      <div className="space-y-4">
        {FAQS.map((f) => (
          <Card key={f.q}><CardHeader><CardTitle className="text-base">{f.q}</CardTitle></CardHeader>
            <CardContent><p className="text-sm text-muted">{f.a}</p></CardContent></Card>
        ))}
      </div>
    </PublicLayout>
  );
}
