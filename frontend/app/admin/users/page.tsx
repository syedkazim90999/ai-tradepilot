"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog } from "@/components/ui/dialog";
import { adminApi, ApiError, type AdminUserOut } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [target, setTarget] = useState<AdminUserOut | null>(null);
  const [action, setAction] = useState<"suspend" | "reactivate" | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async (q?: string) => {
    setLoading(true); setError("");
    try { setUsers(await adminApi.users(q || undefined)); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load users."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const doAction = async () => {
    if (!target || !action) return;
    setBusy(true); setError("");
    try {
      if (action === "suspend") { await adminApi.suspendUser(target.id); setNotice(`${target.email} suspended.`); }
      else { await adminApi.reactivateUser(target.id); setNotice(`${target.email} reactivated.`); }
      setTarget(null); setAction(null); await load(search.trim() || undefined);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Action failed."); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="Users" description="Search, inspect, suspend and reactivate user accounts. Actions are audit-logged." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      {notice && <Alert variant="success" className="mb-4">{notice}</Alert>}
      <div className="mb-4 flex max-w-md gap-2">
        <Input placeholder="Search by email…" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") load(search.trim() || undefined); }} />
        <Button variant="outline" onClick={() => load(search.trim() || undefined)}><Search className="h-4 w-4" /> Search</Button>
      </div>
      <Card>
        <CardHeader><CardTitle>All users</CardTitle><CardDescription>{loading ? "Loading…" : `${users.length} user(s)`}</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : users.length === 0 ? (
            <EmptyState title="No users found" description="Try a different search, or check back after new registrations." />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Email</TableHead><TableHead>Name</TableHead><TableHead>Status</TableHead>
                <TableHead>Verified</TableHead><TableHead>Last login</TableHead><TableHead>Joined</TableHead><TableHead></TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <td className="p-3 font-medium text-white">{u.email}</td>
                    <td className="p-3">{u.full_name || "—"}</td>
                    <td className="p-3">{u.is_suspended ? <Badge variant="destructive">Suspended</Badge> : u.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Disabled</Badge>}</td>
                    <td className="p-3">{u.is_email_verified ? "Yes" : "No"}</td>
                    <td className="p-3 text-muted">{fmtDate(u.last_login_at)}</td>
                    <td className="p-3 text-muted">{fmtDate(u.created_at)}</td>
                    <td className="p-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/admin/users/${u.id}`}><Button size="sm" variant="outline">Details</Button></Link>
                        {u.is_suspended ? (
                          <Button size="sm" variant="success" onClick={() => { setTarget(u); setAction("reactivate"); }}>Reactivate</Button>
                        ) : (
                          <Button size="sm" variant="destructive" onClick={() => { setTarget(u); setAction("suspend"); }}>Suspend</Button>
                        )}
                      </div>
                    </td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <Dialog open={target !== null} onClose={() => { setTarget(null); setAction(null); }}
        title={action === "suspend" ? "Suspend this user?" : "Reactivate this user?"}
        description={target ? `${target.email} — ${action === "suspend" ? "The user will be unable to sign in and their bot stops working until reactivated." : "The user regains access to the platform."} This action is written to the audit log.` : undefined}>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => { setTarget(null); setAction(null); }}>Cancel</Button>
          <Button variant={action === "suspend" ? "destructive" : "success"} onClick={doAction} disabled={busy}>{busy ? "Working…" : action === "suspend" ? "Suspend user" : "Reactivate user"}</Button>
        </div>
      </Dialog>
    </div>
  );
}
