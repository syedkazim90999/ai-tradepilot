import Link from "next/link";
import { ArrowRight, BarChart3, Bot, KeyRound, Radar, ShieldCheck, TrendingUp, Wallet } from "lucide-react";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";

const FEATURES = [
  { icon: Radar, title: "Market scanner", text: "Scans Binance Futures symbols with RSI, MACD, EMA, Bollinger Bands, ATR and VWAP to surface rule-based signals." },
  { icon: Bot, title: "Automated bot", text: "Executes signals with conservative risk defaults: 0.5% risk per trade, 2% daily loss limit, max 2 positions." },
  { icon: ShieldCheck, title: "Risk management first", text: "Stop-loss and take-profit on every trade, leverage caps, and a global pause. No LLM ever places an order." },
  { icon: KeyRound, title: "Encrypted API keys", text: "Your Binance keys are encrypted at rest, shown masked, and withdrawal permission is refused on validation." },
  { icon: BarChart3, title: "Trade analytics", text: "Realized P&L, trade history, open positions and signal history — all from your own account data." },
  { icon: Wallet, title: "Testnet by default", text: "Practice on Binance Futures Testnet with no real money at risk. Production trading stays disabled until explicitly activated." },
];

const FAQS = [
  { q: "Is my money at risk?", a: "On Testnet, no — you trade with test funds. Production trading is disabled by default and requires an explicit Super Admin activation with a written risk acknowledgement." },
  { q: "Does AI TradePilot guarantee profits?", a: "No. No trading system can guarantee returns. Signals are deterministic rule-based calculations, not predictions, and every trade can lose money." },
  { q: "Do you store my Binance API secret in plain text?", a: "No. Secrets are encrypted with Fernet and only the last 4 characters of the key are ever displayed." },
  { q: "Can I cancel anytime?", a: "Yes. Plans are month-to-month and there is a free plan with scanner access and no auto-trading." },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main>
        <section className="mx-auto max-w-7xl px-4 py-20 text-center sm:px-6">
          <span className="inline-block rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-300">Binance Futures Testnet — default &amp; free to try</span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-extrabold leading-tight text-white sm:text-6xl">
            AI-assisted trading on Binance Futures, with risk first.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted">
            AI TradePilot scans the market, scores rule-based signals and automates execution with strict stop-losses,
            leverage caps and daily loss limits. Start on Testnet — no real money at risk.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register"><Button size="lg">Start free on Testnet <ArrowRight className="h-4 w-4" /></Button></Link>
            <Link href="/how-it-works"><Button size="lg" variant="outline">How it works</Button></Link>
          </div>
          <p className="mt-4 text-xs text-muted">No card required for the Free plan. Trading involves substantial risk of loss.</p>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">Everything you need to trade with discipline</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <Card key={f.title}>
                <CardHeader><f.icon className="h-6 w-6 text-blue-400" /><CardTitle className="mt-2">{f.title}</CardTitle></CardHeader>
                <CardContent><CardDescription>{f.text}</CardDescription></CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="border-y border-border bg-[#0D1424]">
          <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
            <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">How it works</h2>
            <div className="mt-8 grid gap-4 md:grid-cols-4">
              {[
                { n: "1", t: "Create an account", d: "Register and verify your email." },
                { n: "2", t: "Connect Binance Testnet", d: "Add a Testnet API key — encrypted and masked, never shown in full." },
                { n: "3", t: "Configure the bot", d: "Set risk per trade, leverage, max positions and your symbols." },
                { n: "4", t: "Review signals & trades", d: "The scanner generates signals; the bot executes within your limits." },
              ].map((s) => (
                <Card key={s.n}>
                  <CardHeader><span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">{s.n}</span><CardTitle className="mt-2">{s.t}</CardTitle></CardHeader>
                  <CardContent><CardDescription>{s.d}</CardDescription></CardContent>
                </Card>
              ))}
            </div>
            <div className="mt-8 text-center"><Link href="/how-it-works"><Button variant="outline">Full walkthrough <ArrowRight className="h-4 w-4" /></Button></Link></div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">Simple pricing</h2>
          <p className="mt-2 text-center text-muted">Start free. Upgrade when you need auto-trading and more positions. Checkout is coming soon.</p>
          <div className="mt-8 grid gap-4 md:grid-cols-4">
            {[
              { name: "Free", price: "$0", desc: "Scanner access, 1 position, 2x leverage.", cta: "Start free" },
              { name: "Basic", price: "$19/mo", desc: "Auto-trading, 2 positions, 3x leverage.", cta: "Choose Basic" },
              { name: "Pro", price: "$49/mo", desc: "Auto-trading, 5 positions, 5x leverage.", cta: "Choose Pro" },
              { name: "Premium", price: "$99/mo", desc: "Auto-trading, 10 positions, 10x leverage.", cta: "Choose Premium" },
            ].map((p) => (
              <Card key={p.name} className={p.name === "Pro" ? "border-blue-500/60" : undefined}>
                <CardHeader><CardTitle>{p.name}</CardTitle><p className="text-2xl font-bold text-white">{p.price}</p></CardHeader>
                <CardContent><CardDescription>{p.desc}</CardDescription>
                  <Link href="/pricing" className="mt-4 block"><Button variant={p.name === "Pro" ? "default" : "outline"} className="w-full">{p.cta}</Button></Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-4 pb-16 sm:px-6">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">Frequently asked questions</h2>
          <div className="mt-8 space-y-4">
            {FAQS.map((f) => (
              <Card key={f.q}><CardHeader><CardTitle className="text-base">{f.q}</CardTitle></CardHeader>
                <CardContent><CardDescription>{f.a}</CardDescription></CardContent></Card>
            ))}
          </div>
          <div className="mt-8 text-center"><Link href="/faq"><Button variant="outline">See all FAQs</Button></Link></div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6">
          <Alert variant="warning" title="Risk disclosure">
            Trading cryptocurrencies and derivatives involves substantial risk of loss and is not suitable for every investor.
            AI TradePilot provides rule-based signals and automation tools — it does not provide financial advice and does not guarantee returns.
            Read the full <Link href="/risk-disclosure" className="underline">Risk Disclosure</Link> before trading.
          </Alert>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
