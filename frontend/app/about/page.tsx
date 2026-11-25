import { PublicLayout } from "@/components/layout/public-layout";

export default function AboutPage() {
  return (
    <PublicLayout title="About AI TradePilot" intro="A disciplined, risk-first approach to automated crypto trading.">
      <p>
        AI TradePilot is an AI-assisted automated trading platform for Binance Futures. It was built around a simple
        observation: most trading losses come not from bad ideas, but from undisciplined execution — oversized positions,
        missing stop-losses, revenge trading after a loss.
      </p>
      <p>
        The platform combines a market scanner (RSI, MACD, EMA, Bollinger Bands, ATR, VWAP) with strict, configurable
        risk rules. Every signal carries an entry, a stop-loss and a take-profit. Every trade is sized by the risk you
        choose. The bot can be paused instantly, and a global emergency stop halts all new trades.
      </p>
      <h2 className="text-xl font-semibold text-white">What we believe</h2>
      <ul className="list-disc space-y-2 pl-5">
        <li><strong className="text-white">Testnet first.</strong> Nobody should risk real money while learning a system. Production trading is disabled by default.</li>
        <li><strong className="text-white">No guaranteed returns.</strong> Any service that promises profits from trading is misleading you. We show your real numbers — wins and losses.</li>
        <li><strong className="text-white">Your keys, your control.</strong> API keys are encrypted, masked, and never given withdrawal permission. You can disconnect at any time.</li>
        <li><strong className="text-white">Transparency over hype.</strong> Signals are deterministic rules you can inspect — the supporting and invalidating conditions are shown with every signal.</li>
      </ul>
      <p>
        AI TradePilot does not provide financial advice. It provides tools. Decisions — and responsibility for them — remain yours.
      </p>
    </PublicLayout>
  );
}
