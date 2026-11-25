import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";

export function PublicLayout({ title, intro, children }: { title: string; intro?: string; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-bold text-white sm:text-4xl">{title}</h1>
        {intro && <p className="mt-3 text-lg text-muted">{intro}</p>}
        <div className="mt-8 space-y-6 text-slate-300 leading-relaxed">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}
