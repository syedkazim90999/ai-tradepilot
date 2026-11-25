import Link from "next/link";
import { CandlestickChart } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-[#0D1424]">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600"><CandlestickChart className="h-5 w-5 text-white" /></span>
            <span className="text-lg font-bold text-white">AI TradePilot</span>
          </div>
          <p className="mt-3 text-sm text-muted">Rule-based AI-assisted trading on Binance Futures. Testnet by default — practice without risking real money.</p>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Product</h3>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li><Link className="hover:text-white" href="/features">Features</Link></li>
            <li><Link className="hover:text-white" href="/how-it-works">How it works</Link></li>
            <li><Link className="hover:text-white" href="/pricing">Pricing</Link></li>
            <li><Link className="hover:text-white" href="/faq">FAQ</Link></li>
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Company</h3>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li><Link className="hover:text-white" href="/about">About</Link></li>
            <li><Link className="hover:text-white" href="/contact">Contact</Link></li>
            <li><Link className="hover:text-white" href="/login">Sign in</Link></li>
            <li><Link className="hover:text-white" href="/register">Create account</Link></li>
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Legal</h3>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li><Link className="hover:text-white" href="/terms">Terms of Service</Link></li>
            <li><Link className="hover:text-white" href="/privacy">Privacy Policy</Link></li>
            <li><Link className="hover:text-white" href="/risk-disclosure">Risk Disclosure</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border px-4 py-5">
        <p className="mx-auto max-w-7xl text-center text-xs leading-relaxed text-muted">
          Trading cryptocurrencies and derivatives involves substantial risk of loss and is not suitable for every investor.
          AI TradePilot runs on Binance Futures Testnet by default and makes no guarantee of returns. Past performance does not predict future results.
          Never trade with money you cannot afford to lose.
        </p>
        <p className="mt-2 text-center text-xs text-muted">© {new Date().getFullYear()} AI TradePilot. All rights reserved.</p>
      </div>
    </footer>
  );
}
