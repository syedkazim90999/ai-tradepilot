"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthLayout } from "@/components/layout/auth-layout";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { adminApi, setAdminToken, ApiError } from "@/lib/api";

export default function AdminLoginPage() {
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
      const res = await adminApi.login(email, password, totp || undefined);
      setAdminToken(res.access_token);
      router.replace("/admin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Admin sign-in failed. Please try again.");
    } finally { setLoading(false); }
  };

  return (
    <AuthLayout title="Super Admin sign-in" description="Restricted area. All actions are audit-logged."
      footer={<>Not an admin? <Link href="/login" className="text-blue-400 hover:underline">User sign-in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}
        <Alert variant="warning">Use the Super Admin credentials created via the first-run admin setup API. Admin tokens are separate from user tokens.</Alert>
        <div className="space-y-2"><Label htmlFor="email">Admin email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></div>
        <div className="space-y-2"><Label htmlFor="password">Password</Label><Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></div>
        <div className="space-y-2"><Label htmlFor="totp">2FA code <span className="font-normal text-muted">(only if enabled)</span></Label><Input id="totp" inputMode="numeric" value={totp} onChange={(e) => setTotp(e.target.value)} placeholder="123456" autoComplete="one-time-code" /></div>
        <Button type="submit" className="w-full" disabled={loading}>{loading ? "Signing in…" : "Sign in as admin"}</Button>
      </form>
    </AuthLayout>
  );
}
