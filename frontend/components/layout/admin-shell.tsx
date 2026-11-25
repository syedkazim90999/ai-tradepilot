"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, Bot, CandlestickChart, LayoutDashboard, LogOut, Menu, ScrollText, Server, Users, Wallet, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { clearAuth, getAdminToken } from "@/lib/api";
import { Button } from "@/components/ui/button";

const NAV = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/trades", label: "Trades", icon: Wallet },
  { href: "/admin/bots", label: "Bots", icon: Bot },
  { href: "/admin/audit", label: "Audit Logs", icon: ScrollText },
  { href: "/admin/system", label: "System", icon: Server },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const isLoginPage = pathname === "/admin/login";
  useEffect(() => {
    if (!isLoginPage && !getAdminToken()) router.replace("/admin/login");
  }, [router, isLoginPage]);

  if (isLoginPage) return <>{children}</>;

  const logout = () => { clearAuth(); router.replace("/admin/login"); };
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
      <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs leading-relaxed text-red-200">
        <Activity className="mb-1 h-4 w-4" />
        Super Admin area. Actions here are audit-logged. Never display API secrets or passwords.
      </div>
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-64 shrink-0 border-r border-border bg-[#0D1424] lg:block">
        <div className="flex h-16 items-center gap-2 border-b border-border px-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-600"><CandlestickChart className="h-5 w-5 text-white" /></span>
          <span className="text-lg font-bold text-white">Admin</span>
          <span className="rounded-full bg-red-600/20 px-2 py-0.5 text-[11px] font-semibold text-red-300">Super Admin</span>
        </div>
        {nav}
      </aside>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/70" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 bg-[#0D1424] shadow-xl">
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
              <span className="font-bold text-white">Admin</span>
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="rounded-md p-1 text-muted hover:text-white"><X className="h-5 w-5" /></button>
            </div>
            {nav}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-border bg-[#0D1424] px-4 sm:px-6">
          <button className="rounded-md p-2 text-slate-300 hover:bg-[#1B2436] lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
          <p className="hidden text-sm text-muted sm:block">Super Admin Panel</p>
          <div className="flex items-center gap-2">
            <Link href="/dashboard"><Button variant="ghost" size="sm">User dashboard</Button></Link>
            <Button variant="outline" size="sm" onClick={logout}><LogOut className="h-4 w-4" /> Sign out</Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
