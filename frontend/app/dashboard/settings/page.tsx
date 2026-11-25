"use client";
import { useEffect, useState } from "react";
import { ShieldCheck, LogOut } from "lucide-react";
import { PageHeader } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Skeleton, TableSkeleton } from "@/components/ui/skeleton";
import { Dialog } from "@/components/ui/dialog";
import { authApi, clearAuth, ApiError, type UserOut, type SessionOut } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<UserOut | null>(null);
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [revokeId, setRevokeId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState("");
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [twofa, setTwofa] = useState<{ otpauth_uri: string; secret: string } | null>(null);
  const [twofaCode, setTwofaCode] = useState("");
  const [disablePw, setDisablePw] = useState("");

  const saveProfile = async () => {
    setBusy(true); setError(""); setNotice("");
    try {
      const u = await authApi.updateProfile(newName.trim());
      setMe(u); setNotice("Profile updated.");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not update profile."); }
    finally { setBusy(false); }
  };

  const changePassword = async () => {
    setBusy(true); setError(""); setNotice("");
    try {
      await authApi.changePassword(currentPw, newPw);
      setNotice("Password changed."); setCurrentPw(""); setNewPw("");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not change password."); }
    finally { setBusy(false); }
  };

  const setup2fa = async () => {
    setBusy(true); setError("");
    try { setTwofa(await authApi.twofaSetup()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not start 2FA setup."); }
    finally { setBusy(false); }
  };

  const verify2fa = async () => {
    setBusy(true); setError("");
    try {
      await authApi.twofaVerify(twofaCode);
      setNotice("2FA enabled."); setTwofa(null); setTwofaCode(""); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not verify 2FA code."); }
    finally { setBusy(false); }
  };

  const disable2fa = async () => {
    setBusy(true); setError("");
    try {
      await authApi.twofaDisable(disablePw);
      setNotice("2FA disabled."); setDisablePw(""); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not disable 2FA."); }
    finally { setBusy(false); }
  };

  const load = async () => {
    setLoading(true); setError("");
    try {
      const [u, s] = await Promise.all([authApi.me(), authApi.sessions()]);
      setMe(u); setSessions(s);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not load settings."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const revoke = async () => {
    if (!revokeId) return;
    setBusy(true); setError("");
    try {
      await authApi.revokeSession(revokeId);
      setNotice("Session revoked."); setRevokeId(null); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not revoke the session."); }
    finally { setBusy(false); }
  };

  const logoutAll = async () => {
    try { await authApi.logout(); } catch { /* cleared regardless */ }
    clearAuth();
    router.replace("/login");
  };

  return (
    <div>
      <PageHeader title="Settings" description="Your profile, security and sessions." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Profile</CardTitle><CardDescription>Account details as stored by the API.</CardDescription></CardHeader>
          <CardContent>
            {loading || !me ? <Skeleton className="h-32 w-full" /> : (
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between"><dt className="text-muted">Email</dt><dd className="font-medium text-white">{me.email}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Full name</dt><dd className="font-medium text-white">{me.full_name || "—"}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Email verified</dt><dd>{me.is_email_verified ? <Badge variant="success">Verified</Badge> : <Badge variant="warning">Not verified</Badge>}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Account status</dt><dd>{me.is_active && !me.is_suspended ? <Badge variant="success">Active</Badge> : <Badge variant="destructive">Disabled / suspended</Badge>}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Member since</dt><dd className="font-medium text-white">{fmtDate(me.created_at)}</dd></div>
              </dl>
            )}
            <div className="mt-4 space-y-2">
              <Label htmlFor="full-name">Full name</Label>
              <div className="flex gap-2">
                <Input id="full-name" value={newName} placeholder={me?.full_name || "Your name"} onChange={(e) => setNewName(e.target.value)} />
                <Button onClick={saveProfile} disabled={busy || !newName.trim()}>Save</Button>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <Label htmlFor="current-pw">Current password</Label>
              <Input id="current-pw" type="password" value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} autoComplete="current-password" />
              <Label htmlFor="new-pw">New password (min 8 characters)</Label>
              <Input id="new-pw" type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} autoComplete="new-password" />
              <Button variant="outline" onClick={changePassword} disabled={busy || !currentPw || newPw.length < 8}>Change password</Button>
              <p className="text-xs text-muted">To reset a forgotten password, sign out and use &ldquo;Forgot your password?&rdquo; on the sign-in page.</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Two-factor authentication (2FA)</CardTitle><CardDescription>Time-based one-time passwords (TOTP).</CardDescription></CardHeader>
          <CardContent>
            {loading || !me ? <Skeleton className="h-24 w-full" /> : (
              <div className="flex items-start gap-3">
                <ShieldCheck className={`h-5 w-5 ${me.totp_enabled ? "text-green-400" : "text-muted"}`} />
                <div className="flex-1">
                  <p className="font-medium text-white">{me.totp_enabled ? "2FA is enabled" : "2FA is not enabled"}</p>
                  <p className="mt-1 text-sm text-muted">
                    {me.totp_enabled
                      ? "Your sign-ins require a TOTP code from your authenticator app."
                      : "Add your account to an authenticator app (Google/Microsoft Authenticator, Authy) and verify a code to enable 2FA."}
                  </p>
                  {!me.totp_enabled && !twofa && (
                    <Button className="mt-3" variant="outline" onClick={setup2fa} disabled={busy}>Set up 2FA</Button>
                  )}
                  {!me.totp_enabled && twofa && (
                    <div className="mt-3 space-y-2">
                      <p className="text-sm text-muted">Add this account to your authenticator app with the secret below (or the otpauth URI), then enter the 6-digit code it shows.</p>
                      <p className="break-all rounded-lg bg-[#0D1424] p-3 font-mono text-xs text-white">{twofa.secret}</p>
                      <p className="break-all text-xs text-muted">{twofa.otpauth_uri}</p>
                      <div className="flex gap-2">
                        <Input placeholder="6-digit code" value={twofaCode} onChange={(e) => setTwofaCode(e.target.value)} maxLength={6} />
                        <Button onClick={verify2fa} disabled={busy || twofaCode.length !== 6}>Verify &amp; enable</Button>
                      </div>
                    </div>
                  )}
                  {me.totp_enabled && (
                    <div className="mt-3 space-y-2">
                      <Label htmlFor="disable-pw">Current password (to disable 2FA)</Label>
                      <div className="flex gap-2">
                        <Input id="disable-pw" type="password" value={disablePw} onChange={(e) => setDisablePw(e.target.value)} />
                        <Button variant="destructive" onClick={disable2fa} disabled={busy || !disablePw}>Disable 2FA</Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <Card className="mt-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <div><CardTitle>Active sessions</CardTitle><CardDescription>Every sign-in creates a session. Revoke any you do not recognise.</CardDescription></div>
          <Button variant="outline" size="sm" onClick={logoutAll}><LogOut className="h-4 w-4" /> Sign out everywhere</Button>
        </CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : sessions.length === 0 ? (
            <p className="text-sm text-muted">No sessions found.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((s) => (
                <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-[#0D1424] px-3 py-2">
                  <div className="text-sm">
                    <span className="font-medium text-white">{s.token_type}</span>
                    <span className="text-muted"> · IP {s.ip_address || "unknown"} · created {fmtDate(s.created_at)} · expires {fmtDate(s.expires_at)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={s.is_revoked ? "secondary" : "success"}>{s.is_revoked ? "Revoked" : "Active"}</Badge>
                    {!s.is_revoked && <Button size="sm" variant="outline" onClick={() => setRevokeId(s.id)}>Revoke</Button>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <Dialog open={revokeId !== null} onClose={() => setRevokeId(null)} title="Revoke this session?"
        description="The session's tokens will stop working immediately. If this is your current session you will be signed out.">
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setRevokeId(null)}>Cancel</Button>
          <Button variant="destructive" onClick={revoke} disabled={busy}>Revoke session</Button>
        </div>
      </Dialog>
    </div>
  );
}
