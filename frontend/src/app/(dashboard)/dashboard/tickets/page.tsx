"use client";
import Link from "next/link";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, PageLoader, statusLabel, statusTone } from "@/components/ui";
import { api } from "@/lib/api";
import { timeAgo, useFetch } from "@/lib/hooks";
import type { Ticket, User } from "@/lib/types";

const select = "rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm focus:border-teal-700 focus:outline-none";

export default function Tickets() {
  const [status, setStatus] = useState("");
  const { data, error, reload } = useFetch<Ticket[]>(`/tickets${status ? `?status=${status}` : ""}`, 10000);
  const { data: team } = useFetch<User[]>("/team");
  const [err, setErr] = useState<string | null>(null);

  async function patch(id: string, body: Record<string, unknown>) {
    setErr(null);
    try { await api(`/tickets/${id}`, { method: "PATCH", json: body }); await reload(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Update failed"); }
  }

  return (
    <>
      <PageHeader title="Tickets" subtitle="Conversations that need a human." action={
        <select aria-label="Filter by status" className={select} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option><option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option>
        </select>} />
      {err && <p role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{err}</p>}
      {error ? <ErrorState message={error.message} onRetry={reload} /> : !data ? <PageLoader /> : data.length === 0 ? (
        <Card><EmptyState title="No tickets" body="Tickets are created when a customer asks for a human or the AI can't help twice in a row." /></Card>
      ) : (
        <div className="space-y-3">
          {data.map((t) => (
            <Card key={t.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={statusTone[t.status]}>{statusLabel(t.status)}</Badge>
                <Badge tone={t.priority === "high" ? "red" : t.priority === "low" ? "gray" : "blue"}>{statusLabel(t.priority)} priority</Badge>
                <span className="text-xs text-stone-500">{timeAgo(t.created_at)}</span>
              </div>
              <p className="mt-2 text-sm font-medium text-stone-900">{t.escalation_reason}</p>
              {t.summary && <p className="mt-1 text-sm text-stone-600">{t.summary}</p>}
              <p className="mt-1 text-xs text-stone-500">Customer email: {t.customer_email ?? "not provided"}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <select aria-label="Status" className={select} value={t.status} onChange={(e) => patch(t.id, { status: e.target.value })}>
                  <option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option>
                </select>
                <select aria-label="Priority" className={select} value={t.priority} onChange={(e) => patch(t.id, { priority: e.target.value })}>
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
                </select>
                <select aria-label="Assignee" className={select} value={t.assigned_to ?? ""} onChange={(e) => patch(t.id, { assigned_to: e.target.value || null })}>
                  <option value="">Unassigned</option>
                  {team?.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                </select>
                <Link href={`/dashboard/conversations?c=${t.conversation_id}`} className="ml-auto"><Button variant="secondary">Open conversation</Button></Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
