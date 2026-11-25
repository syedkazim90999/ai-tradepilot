"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bell, Bot, CandlestickChart, CreditCard, KeyRound, LayoutDashboard, LogOut,
  Menu, Radio, Settings, ShieldCheck, Signal, Wallet, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { authApi, clearAuth, getAccessToken, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/connections", label: "Connections", icon: KeyRound },
  { href: "/dashboard/bot", label: "Trading Bot", icon: Bot },
  { href: "/dashboard/signals", label: "Signals", icon: Signal },
  { href: "/dashboard/trades", label: "Trade History", icon: Wallet },
  { href: "/dashboard/positions", label: "Positions", icon: Radio },
  { href: "/dashboard/notifications", label: "Notifications", icon: Bell },
  { href: "/dashboard/subscription", label: "Subscription", icon: CreditCard },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState<string>("");

  useEffect(() => {
    if (!getAccessToken()) { router.replace("/login"); return; }
    authApi.me().then((u) => setEmail(u.email)).catch((e: unknown) => {
      if (e instanceof ApiError && e.status === 401) router.replace("/login");
    });
  }, [router]);

  const logout = async () => {
    try { await authApi.logout(); } catch { /* token cleared regardless */ }
    clearAuth();
    router.replace("/login");
  };

  const nav = (
    <nav className="flex flex-col gap-1 p-3">
      {NAV.map((item) => {
        const active = pathname === item.href;
        return (
          <Link key={item.href} href={item.href} onClick={() => setOpen(false)}
            className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              active ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-[#1B2436] hover:text-white")}>
            <item.icon className="h-4 w-4" /> {item.label}
          </Link>
        );
      })}
      <div className="mt-4 rounded-lg border border-border bg-[#0D1424] p-3 text-xs leading-relaxed text-muted">
        <ShieldCheck className="mb-1 h-4 w-4 text-green-400" />
        Testnet by default. Production trading is disabled unless a Super Admin explicitly activates it.
      </div>
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-[#0D1424] lg:block">
        <div className="flex h-16 items-center gap-2 border-b border-border px-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600"><CandlestickChart className="h-5 w-5 text-white" /></span>
          <span className="text-lg font-bold text-white">AI TradePilot</span>
        </div>
        {nav}
      </aside>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/70" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 bg-[#0D1424] shadow-xl">
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
              <span className="font-bold text-white">AI TradePilot</span>
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="rounded-md p-1 text-muted hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            {nav}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-border bg-[#0D1424] px-4 sm:px-6">
          <button className="rounded-md p-2 text-slate-300 hover:bg-[#1B2436] lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <p className="hidden truncate text-sm text-muted sm:block">{email || "Dashboard"}</p>
          <div className="flex items-center gap-2">
            <Link href="/dashboard/notifications"><Button variant="ghost" size="sm"><Bell className="h-4 w-4" /> <span className="hidden sm:inline">Notifications</span></Button></Link>
            <Button variant="outline" size="sm" onClick={logout}><LogOut className="h-4 w-4" /> Sign out</Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
