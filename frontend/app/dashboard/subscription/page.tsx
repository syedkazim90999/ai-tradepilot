"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Check, CreditCard } from "lucide-react";
import { PageHeader } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { userApi, ApiError, type Plan, type MySubscription } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function SubscriptionPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [mine, setMine] = useState<MySubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([userApi.plans(), userApi.mySubscription()])
      .then(([p, m]) => { setPlans(p); setMine(m); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load subscription info."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="Subscription" description="Your current plan and what each plan includes." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <Alert className="mb-4" title="Checkout coming soon">
        Paid plans cannot be purchased yet — checkout is coming soon. Your account currently runs on the plan shown below, and plan changes will be possible once checkout is live.
      </Alert>
      {loading ? <Skeleton className="h-28 w-full" /> : mine && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Current plan</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-center gap-4">
            <Badge className="text-base px-3 py-1">{mine.plan}</Badge>
            <Badge variant={mine.status === "active" ? "success" : "secondary"}>{mine.status}</Badge>
            <span className="text-sm text-muted">Since {fmtDate(mine.started_at)}{mine.expires_at ? ` · Expires ${fmtDate(mine.expires_at)}` : " · No expiry"}</span>
            <span className="text-sm text-muted">Max positions: {mine.features.max_positions} · Max leverage: {mine.features.max_leverage}x · Auto-trading: {mine.features.auto_trading ? "yes" : "no"} · Scanner: {mine.features.scanner ? "yes" : "no"}</span>
          </CardContent>
        </Card>
      )}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-64" />)}</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {plans.map((p) => {
            const current = mine?.plan === p.name;
            return (
              <Card key={p.name} className={current ? "border-blue-500/60" : undefined}>
                <CardHeader>
                  <div className="flex items-center justify-between"><CardTitle>{p.name}</CardTitle>{current && <Badge>Current</Badge>}</div>
                  <p className="text-3xl font-bold text-white">${p.price_usd}<span className="text-sm font-normal text-muted">/mo</span></p>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm text-slate-300">
                    <li className="flex gap-2"><Check className="h-4 w-4 shrink-0 text-green-400" />Scanner: {p.scanner ? "included" : "not included"}</li>
                    <li className="flex gap-2"><Check className="h-4 w-4 shrink-0 text-green-400" />Auto-trading: {p.auto_trading ? "included" : "not included"}</li>
                    <li className="flex gap-2"><Check className="h-4 w-4 shrink-0 text-green-400" />{p.max_positions} max position{p.max_positions === 1 ? "" : "s"}</li>
                    <li className="flex gap-2"><Check className="h-4 w-4 shrink-0 text-green-400" />{p.max_leverage}x max leverage</li>
                  </ul>
                  <Link href="/pricing" className="mt-5 block">
                    <Button variant={current ? "outline" : "default"} className="w-full" disabled={current}>{current ? "Current plan" : "View plan"}</Button>
                  </Link>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
      <p className="mt-4 flex items-center gap-2 text-sm text-muted"><CreditCard className="h-4 w-4" /> No payment method is stored — checkout is not live yet, so nothing can be charged.</p>
    </div>
  );
}
