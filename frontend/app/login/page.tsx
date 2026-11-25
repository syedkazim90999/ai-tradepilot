"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { authApi, setTokens, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const tokens = await authApi.login(email, password, totp || undefined);
      setTokens(tokens.access_token, tokens.refresh_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed. Please try again.");
    } finally { setLoading(false); }
  };

  return (
    <AuthLayout title="Sign in" description="Access your AI TradePilot dashboard."
      footer={<>No account yet? <Link href="/register" className="text-blue-400 hover:underline">Create one</Link> · <Link href="/admin/login" className="text-blue-400 hover:underline">Admin sign-in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}
        <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></div>
        <div className="space-y-2"><Label htmlFor="password">Password</Label><Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></div>
        <div className="space-y-2"><Label htmlFor="totp">2FA code <span className="font-normal text-muted">(only if enabled)</span></Label><Input id="totp" inputMode="numeric" value={totp} onChange={(e) => setTotp(e.target.value)} placeholder="123456" autoComplete="one-time-code" /></div>
        <Button type="submit" className="w-full" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</Button>
        <p className="text-center text-sm"><Link href="/forgot-password" className="text-blue-400 hover:underline">Forgot your password?</Link></p>
      </form>
    </AuthLayout>
  );
}
