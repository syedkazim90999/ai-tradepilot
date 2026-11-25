import * as React from "react";
import { cn } from "@/lib/utils";
export function Switch({ checked, onCheckedChange, disabled, label }: {
  checked: boolean; onCheckedChange: (v: boolean) => void; disabled?: boolean; label?: string;
}) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label || "Toggle"}
      disabled={disabled} onClick={() => onCheckedChange(!checked)}
      className={cn("relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors disabled:opacity-50",
        checked ? "bg-blue-600" : "bg-slate-700")}>
      <span className={cn("inline-block h-4 w-4 transform rounded-full bg-white transition-transform", checked ? "translate-x-6" : "translate-x-1")} />
    </button>
  );
}
