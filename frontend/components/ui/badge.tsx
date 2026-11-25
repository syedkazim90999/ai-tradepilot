import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const badgeVariants = cva("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  { variants: { variant: {
    default: "border-transparent bg-blue-600/20 text-blue-300",
    secondary: "border-transparent bg-slate-700/40 text-slate-300",
    success: "border-transparent bg-green-600/20 text-green-300",
    destructive: "border-transparent bg-red-600/20 text-red-300",
    warning: "border-transparent bg-amber-600/20 text-amber-300",
    outline: "text-slate-300 border-border",
  } }, defaultVariants: { variant: "default" } });
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}
function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
export { Badge, badgeVariants };
