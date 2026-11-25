"use client";
import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "@/components/layout/shared";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { TableSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { adminApi, ApiError, type AuditLogOut } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function AdminAuditPage() {
  const [logs, setLogs] = useState<AuditLogOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    adminApi.auditLogs(100)
      .then(setLogs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load audit logs."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="Audit logs" description="Append-only record of Super Admin actions: suspensions, bot pauses, setting changes and maintenance." />
      {error && <Alert variant="error" className="mb-4">{error}</Alert>}
      <Card>
        <CardHeader><CardTitle>Audit trail</CardTitle><CardDescription>{loading ? "Loading…" : `${logs.length} entr${logs.length === 1 ? "y" : "ies"}`}</CardDescription></CardHeader>
        <CardContent>
          {loading ? <TableSkeleton /> : logs.length === 0 ? (
            <EmptyState title="No audit entries yet" description="Admin actions such as suspending a user or pausing all bots are recorded here automatically." />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Action</TableHead><TableHead>Target</TableHead><TableHead>Admin ID</TableHead><TableHead>Details</TableHead><TableHead>When</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {logs.map((l) => (
                  <TableRow key={l.id}>
                    <td className="p-3"><Badge variant="secondary">{l.action}</Badge></td>
                    <td className="p-3 text-muted">{l.target_type ? `${l.target_type}:${l.target_id?.slice(0, 8) ?? ""}…` : "—"}</td>
                    <td className="p-3 font-mono text-xs text-muted">{l.admin_id.slice(0, 8)}…</td>
                    <td className="p-3 text-xs text-muted">{l.details ? JSON.stringify(l.details) : "—"}</td>
                    <td className="p-3 text-muted">{fmtDate(l.created_at)}</td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
