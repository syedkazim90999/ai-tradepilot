import Link from "next/link";
import { CandlestickChart } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function AuthLayout({ title, description, children, footer }: {
  title: string; description?: string; children: React.ReactNode; footer?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="flex h-16 items-center px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600"><CandlestickChart className="h-5 w-5 text-white" /></span>
          <span className="text-lg font-bold text-white">AI TradePilot</span>
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <Card className="w-full max-w-md">
          <CardHeader><CardTitle className="text-xl">{title}</CardTitle>{description && <CardDescription>{description}</CardDescription>}</CardHeader>
          <CardContent>{children}{footer && <div className="mt-6 border-t border-border pt-4 text-center text-sm text-muted">{footer}</div>}</CardContent>
        </Card>
      </main>
      <p className="px-4 pb-6 text-center text-xs text-muted">Trading involves substantial risk of loss. Live trading — real money at risk. No guaranteed returns.</p>
    </div>
  );
}
