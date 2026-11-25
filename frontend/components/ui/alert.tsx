import * as React from "react";
import { AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
export function Alert({ variant = "info", title, children, className }: {
  variant?: "info" | "warning" | "error" | "success"; title?: string; children?: React.ReactNode; className?: string;
}) {
  const Icon = variant === "warning" || variant === "error" ? AlertTriangle : variant === "success" ? CheckCircle2 : Info;
  const styles = {
    info: "border-blue-500/30 bg-blue-500/10 text-blue-200",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-200",
    error: "border-red-500/30 bg-red-500/10 text-red-200",
    success: "border-green-500/30 bg-green-500/10 text-green-200",
  }[variant];
  return (
    <div role="alert" className={cn("flex gap-3 rounded-lg border p-4 text-sm", styles, className)}>
      <Icon className="h-5 w-5 shrink-0" />
      <div>{title && <p className="font-semibold">{title}</p>}{children && <div className="mt-1 opacity-90">{children}</div>}</div>
    </div>
  );
}
