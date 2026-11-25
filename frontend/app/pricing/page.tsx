import Link from "next/link";
import { Check } from "lucide-react";
import { PublicLayout } from "@/components/layout/public-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

const PLANS = [
  { name: "Free", price: "$0", period: "forever", features: ["Market scanner", "1 max position", "2x max leverage", "Trade history & signals", "No auto-trading"], cta: "Start free" },
  { name: "Basic", price: "$19", period: "/month", features: ["Everything in Free", "Auto-trading", "2 max positions", "3x max leverage"], cta: "Choose Basic" },
  { name: "Pro", price: "$49", period: "/month", features: ["Everything in Basic", "5 max positions", "5x max leverage", "Priority scanner"], cta: "Choose Pro" },
  { name: "Premium", price: "$99", period: "/month", features: ["Everything in Pro", "10 max positions", "10x max leverage", "All future features"], cta: "Choose Premium" },
];

export default function PricingPage() {
  return (
    <PublicLayout title="Pricing" intro="Start free on Testnet. Upgrade only when you need auto-trading and higher limits.">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((p) => (
          <Card key={p.name} className={p.name === "Pro" ? "border-blue-500/60" : undefined}>
            <CardHeader>
              <CardTitle>{p.name}</CardTitle>
              <p className="text-3xl font-bold text-white">{p.price}<span className="text-sm font-normal text-muted">{p.period}</span></p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-slate-300">
                {p.features.map((f) => (<li key={f} className="flex gap-2"><Check className="h-4 w-4 shrink-0 text-green-400" />{f}</li>))}
              </ul>
              <Link href="/register" className="mt-5 block"><Button variant={p.name === "Pro" ? "default" : "outline"} className="w-full">{p.cta}</Button></Link>
            </CardContent>
          </Card>
        ))}
      </div>
      <Alert title="Checkout coming soon">
        Paid plans are not purchasable yet — checkout is coming soon. Registering today gives you the Free plan immediately, and your current plan is always visible under Dashboard → Subscription.
      </Alert>
      <p className="text-sm text-muted">Prices in USD. Plans are month-to-month and can be cancelled at any time. A paid plan buys platform features — it does not buy trading profits, and no returns are guaranteed.</p>
    </PublicLayout>
  );
}
