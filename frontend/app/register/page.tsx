"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { authApi, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const res = await authApi.register(email, password, fullName || undefined);
      setDevToken(res.verification_token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed. Please try again.");
    } finally { setLoading(false); }
  };

  const verifyNow = async () => {
    if (!devToken) return;
    try { await authApi.verifyEmail(devToken); router.replace("/login"); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Verification failed."); }
  };

  return (
    <AuthLayout title="Create your account" description="Start free on Binance Futures Testnet."
      footer={<>Already have an account? <Link href="/login" className="text-blue-400 hover:underline">Sign in</Link></>}>
      {devToken ? (
        <div className="space-y-4">
          <Alert variant="success" title="Account created">Your account was created. In this development setup no real email is sent, so the verification token is shown below instead.</Alert>
          <Alert title="Development only — verification token">
            <code className="break-all text-xs">{devToken}</code>
          </Alert>
          <Button className="w-full" onClick={verifyNow}>Verify email &amp; go to sign-in</Button>
          <p className="text-center text-sm text-muted">In production this token is delivered by email only.</p>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <div className="space-y-2"><Label htmlFor="fullName">Full name</Label><Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" /></div>
          <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></div>
          <div className="space-y-2"><Label htmlFor="password">Password <span className="font-normal text-muted">(min. 8 characters)</span></Label><Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" /></div>
          <Button type="submit" className="w-full" disabled={loading}>{loading ? "Creating account…" : "Create account"}</Button>
          <p className="text-xs leading-relaxed text-muted">By creating an account you agree to the <Link href="/terms" className="text-blue-400 hover:underline">Terms of Service</Link> and acknowledge the <Link href="/risk-disclosure" className="text-blue-400 hover:underline">Risk Disclosure</Link>. Trading involves substantial risk of loss.</p>
        </form>
      )}
    </AuthLayout>
  );
}
