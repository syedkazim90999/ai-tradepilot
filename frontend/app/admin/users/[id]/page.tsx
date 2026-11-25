"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { PageHeader } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { adminApi, ApiError, type AdminUserOut } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function AdminUserDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [user, setUser] = useState<AdminUserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setUser(await adminApi.user(id)); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load this user."); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const toggleSuspend = async () => {
    if (!user) return;
    setBusy(true); setError("");
    try {
      if (user.is_suspended) { await adminApi.reactivateUser(user.id); setNotice("User reactivated."); }
      else { await adminApi.suspendUser(user.id); setNotice("User suspended."); }
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Action failed."); }
    finally { setBusy(false); }
  };

  const pauseBot = async () => {
    if (!user) return;
    setBusy(true); setError("");
    try { await adminApi.pauseUserBot(user.id); setNotice("User bot paused."); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not pause the bot (the user may have no bot settings yet)."); }
    finally { setBusy(false); }
  };
  const resumeBot = async () => {
    if (!user) return;
    setBusy(true); setError("");
    try { await adminApi.resumeUserBot(user.id); setNotice("User bot resumed."); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not resume the bot (the user may have no bot settings yet)."); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="User detail" description={`User ID: ${id}`}
        action={<Link href="/admin/users"><Button variant="outline" size="sm"><ArrowLeft className="h-4 w-4" /> Back to users</Button></Link>} />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      {loading || !user ? <Skeleton className="h-64 w-full" /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>{user.email}</CardTitle><CardDescription>Registered {fmtDate(user.created_at)}</CardDescription></CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between"><dt className="text-muted">Full name</dt><dd className="font-medium text-white">{user.full_name || "—"}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Status</dt><dd>{user.is_suspended ? <Badge variant="destructive">Suspended</Badge> : user.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Disabled</Badge>}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Email verified</dt><dd className="font-medium text-white">{user.is_email_verified ? "Yes" : "No"}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">Last login</dt><dd className="font-medium text-white">{fmtDate(user.last_login_at)}</dd></div>
                <div className="flex justify-between"><dt className="text-muted">User ID</dt><dd className="font-mono text-xs text-white">{user.id}</dd></div>
              </dl>
              <p className="mt-4 text-xs leading-relaxed text-muted">No secrets are shown here. The admin API never returns passwords or API keys, and this page never asks for them.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Admin actions</CardTitle><CardDescription>Every action is written to the audit log.</CardDescription></CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant={user.is_suspended ? "success" : "destructive"} onClick={toggleSuspend} disabled={busy}>
                {user.is_suspended ? "Reactivate user" : "Suspend user"}
              </Button>
              <Button variant="outline" onClick={pauseBot} disabled={busy}>Pause user bot</Button>
              <Button variant="outline" onClick={resumeBot} disabled={busy}>Resume user bot</Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
