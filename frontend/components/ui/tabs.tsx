import * as React from "react";
import { cn } from "@/lib/utils";

export function Tabs({ tabs, active, onChange, className }: {
  tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void; className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap gap-1 rounded-lg bg-[#0D1424] border border-border p-1", className)} role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={active === t.id} onClick={() => onChange(t.id)}
          className={cn("rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            active === t.id ? "bg-blue-600 text-white" : "text-muted hover:text-white hover:bg-[#1B2436]")}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
