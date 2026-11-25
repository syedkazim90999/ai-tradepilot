"use client";
import Link from "next/link";
import { useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { authApi, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const res = await authApi.forgotPassword(email);
      setDevToken(res.dev_reset_token || null);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally { setLoading(false); }
  };

  return (
    <AuthLayout title="Reset your password" description="Enter your account email and we'll send a reset link."
      footer={<><Link href="/login" className="text-blue-400 hover:underline">Back to sign-in</Link></>}>
      {done ? (
        <div className="space-y-4">
          <Alert variant="success" title="Check your email">If an account exists for that email, a password reset link was sent. The link expires in 1 hour.</Alert>
          {devToken && (
            <Alert title="Development only — reset token">
              <p>No real email is configured in this dev setup, so the reset token is shown here:</p>
              <code className="mt-1 block break-all text-xs">{devToken}</code>
              <Link href={`/reset-password?token=${encodeURIComponent(devToken)}`} className="mt-2 inline-block text-blue-400 hover:underline">Continue to reset password →</Link>
            </Alert>
          )}
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}
          <div className="space-y-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></div>
          <Button type="submit" className="w-full" disabled={loading}>{loading ? "Sending…" : "Send reset link"}</Button>
        </form>
      )}
    </AuthLayout>
  );
}
