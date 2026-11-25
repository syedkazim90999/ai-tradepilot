"use client";
import { useEffect, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { userApi, ApiError, type NotificationOut } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

export default function NotificationsPage() {
  const [notes, setNotes] = useState<NotificationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try { setNotes(await userApi.notifications()); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not load notifications."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const markRead = async (id: string) => {
    try { await userApi.markNotificationRead(id); setNotes((ns) => ns.map((n) => (n.id === id ? { ...n, is_read: true } : n))); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Could not mark as read."); }
  };

  const markAll = async () => {
    for (const n of notes.filter((n) => !n.is_read)) {
      try { await userApi.markNotificationRead(n.id); } catch { /* continue with the rest */ }
    }
    await load();
  };

  const unread = notes.filter((n) => !n.is_read).length;

  return (
    <div>
      <PageHeader title="Notifications" description="Bot events, trade alerts and account messages."
        action={unread > 0 ? <Button variant="outline" size="sm" onClick={markAll}><CheckCheck className="h-4 w-4" /> Mark all as read</Button> : undefined} />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <Card>
        <CardHeader><CardTitle>All notifications</CardTitle><CardDescription>{loading ? "Loading…" : `${unread} unread of ${notes.length}`}</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : notes.length === 0 ? (
            <EmptyState title="No notifications" description="Notifications about bot starts/stops, trades and account events will appear here." />
          ) : (
            <div className="space-y-3">
              {notes.map((n) => (
                <div key={n.id} className={`flex items-start gap-3 rounded-lg border p-4 ${n.is_read ? "border-border bg-[#0D1424]" : "border-blue-500/40 bg-blue-500/5"}`}>
                  <Bell className={`mt-0.5 h-4 w-4 shrink-0 ${n.is_read ? "text-muted" : "text-blue-400"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-white">{n.title}</span>
                      <Badge variant="secondary">{n.type}</Badge>
                      {!n.is_read && <Badge>Unread</Badge>}
                      <span className="text-xs text-muted">{timeAgo(n.created_at)}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-300">{n.message}</p>
                  </div>
                  {!n.is_read && <Button variant="ghost" size="sm" onClick={() => markRead(n.id)}>Mark read</Button>}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
