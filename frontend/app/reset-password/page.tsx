"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { authApi, ApiError } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reset failed. The token may be invalid or expired.");
    } finally { setLoading(false); }
  };

  if (done) {
    return (
      <div className="space-y-4">
        <Alert variant="success" title="Password reset">Your password has been changed. You can now sign in with your new password.</Alert>
        <Button className="w-full" onClick={() => router.replace("/login")}>Go to sign-in</Button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      {error && <Alert variant="error">{error}</Alert>}
      <div className="space-y-2"><Label htmlFor="token">Reset token</Label><Input id="token" value={token} onChange={(e) => setToken(e.target.value)} required placeholder="Paste the token from your reset email" /></div>
      <div className="space-y-2"><Label htmlFor="password">New password <span className="font-normal text-muted">(min. 8 characters)</span></Label><Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" /></div>
      <Button type="submit" className="w-full" disabled={loading}>{loading ? "Resetting…" : "Reset password"}</Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthLayout title="Set a new password" description="Paste your reset token and choose a new password."
      footer={<><Link href="/login" className="text-blue-400 hover:underline">Back to sign-in</Link></>}>
      <Suspense><ResetForm /></Suspense>
    </AuthLayout>
  );
}
