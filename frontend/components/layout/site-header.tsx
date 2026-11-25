"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { CandlestickChart, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const LINKS = [
  { href: "/features", label: "Features" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
  { href: "/faq", label: "FAQ" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600"><CandlestickChart className="h-5 w-5 text-white" /></span>
          <span className="text-lg font-bold text-white">AI TradePilot</span>
          <span className="hidden rounded-full bg-blue-600/20 px-2 py-0.5 text-[11px] font-semibold text-blue-300 sm:inline">Testnet</span>
        </Link>
        <nav className="hidden items-center gap-1 lg:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href}
              className={cn("rounded-md px-3 py-2 text-sm transition-colors", pathname === l.href ? "text-white bg-[#1B2436]" : "text-muted hover:text-white")}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden items-center gap-2 lg:flex">
          <Link href="/login"><Button variant="ghost">Sign in</Button></Link>
          <Link href="/register"><Button>Get started</Button></Link>
        </div>
        <button className="rounded-md p-2 text-slate-300 hover:bg-[#1B2436] lg:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-border px-4 py-3 lg:hidden">
          <nav className="flex flex-col gap-1">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-[#1B2436]">{l.label}</Link>
            ))}
            <div className="mt-2 flex gap-2">
              <Link href="/login" className="flex-1"><Button variant="outline" className="w-full">Sign in</Button></Link>
              <Link href="/register" className="flex-1"><Button className="w-full">Get started</Button></Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
