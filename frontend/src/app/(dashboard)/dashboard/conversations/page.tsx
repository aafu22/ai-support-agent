"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, PageLoader, Spinner, Textarea, statusLabel, statusTone } from "@/components/ui";
import { api } from "@/lib/api";
import { timeAgo, useFetch } from "@/lib/hooks";
import type { Conversation, ConversationDetail } from "@/lib/types";

const roleStyle = {
  customer: "bg-teal-800 text-white rounded-br-sm",
  assistant: "bg-stone-100 text-stone-800 rounded-bl-sm",
  human_agent: "bg-amber-100 text-amber-950 rounded-bl-sm",
  system: "bg-stone-50 text-stone-500",
} as const;
const roleLabel = { customer: "Customer", assistant: "AI", human_agent: "Support agent", system: "System" } as const;

function Detail({ id, onChanged }: { id: string; onChanged: () => void }) {
  const { data, error, loading, reload } = useFetch<ConversationDetail>(`/conversations/${id}`, 5000);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [data?.messages.length]);

  if (loading && !data) return <PageLoader />;
  if (error || !data) return <ErrorState message={error?.message ?? "Not found"} onRetry={reload} />;

  async function send(e: React.FormEvent) {
    e.preventDefault(); if (!text.trim()) return;
    setBusy(true); setErr(null);
    try { await api(`/conversations/${id}/reply`, { method: "POST", json: { content: text } }); setText(""); await reload(); onChanged(); }
    catch (x) { setErr(x instanceof Error ? x.message : "Failed to send"); }
    finally { setBusy(false); }
  }

  return (
    <div className="flex h-[70vh] flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-stone-100 p-4">
        <Badge tone={statusTone[data.status]}>{statusLabel(data.status)}</Badge>
        <span className="text-sm text-stone-600">{data.customer_email ?? "Anonymous customer"}</span>
        {data.status === "ai_active" && <span className="text-xs text-stone-500">Replying will pause the AI.</span>}
      </div>
      {data.summary && <p className="border-b border-stone-100 bg-amber-50/60 px-4 py-2 text-sm text-stone-700"><span className="font-medium">AI summary:</span> {data.summary}</p>}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {data.messages.map((m) => (
          <div key={m.id} className={`flex max-w-[85%] flex-col ${m.role === "customer" ? "ml-auto items-end" : ""}`}>
            <span className="mb-0.5 text-xs text-stone-500">{roleLabel[m.role]} · {timeAgo(m.created_at)}{m.confidence != null && m.role === "assistant" ? ` · match ${(m.confidence * 100).toFixed(0)}%` : ""}</span>
            <div className={`whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${roleStyle[m.role]}`}>{m.content}</div>
            {m.sources && m.sources.length > 0 && (
              <ul className="mt-1 space-y-0.5 text-xs text-stone-500">
                {m.sources.map((s) => <li key={s.id}>[{s.id}] {s.title}{s.page ? ` · p.${s.page}` : ""}</li>)}
              </ul>
            )}
            {m.is_unanswered && m.role === "customer" && <span className="mt-1"><Badge tone="amber">AI couldn&apos;t answer</Badge></span>}
          </div>
        ))}
        <div ref={end} />
      </div>
      <form onSubmit={send} className="border-t border-stone-100 p-3">
        {err && <p className="mb-2 text-sm text-red-700">{err}</p>}
        <div className="flex gap-2">
          <Textarea rows={2} aria-label="Reply to customer" placeholder="Reply as a human agent…" value={text} maxLength={4000} onChange={(e) => setText(e.target.value)} className="flex-1" />
          <Button type="submit" disabled={busy || !text.trim()}>{busy && <Spinner />} Send</Button>
        </div>
      </form>
    </div>
  );
}

function Inner() {
  const params = useSearchParams();
  const [selected, setSelected] = useState<string | null>(params.get("c"));
  const [status, setStatus] = useState("");
  const { data, error, reload } = useFetch<Conversation[]>(`/conversations${status ? `?status=${status}` : ""}`, 8000);

  return (
    <>
      <PageHeader title="Conversations" subtitle="Everything customers have asked, with the sources the AI used." />
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <Card className="overflow-hidden">
          <div className="flex gap-1 border-b border-stone-100 p-2">
            {[["", "All"], ["escalated", "Escalated"], ["ai_active", "AI"], ["resolved", "Resolved"]].map(([v, l]) => (
              <button key={v} onClick={() => setStatus(v)} className={`rounded-md px-2.5 py-1 text-xs font-medium ${status === v ? "bg-teal-800 text-white" : "text-stone-600 hover:bg-stone-100"}`}>{l}</button>
            ))}
          </div>
          {error ? <div className="p-3"><ErrorState message={error.message} onRetry={reload} /></div> : !data ? <PageLoader /> : data.length === 0 ? (
            <EmptyState title="No conversations" body="They appear here once customers start chatting." />
          ) : (
            <ul className="max-h-[65vh] divide-y divide-stone-100 overflow-y-auto">
              {data.map((c) => (
                <li key={c.id}>
                  <button onClick={() => setSelected(c.id)} className={`w-full px-4 py-3 text-left hover:bg-stone-50 ${selected === c.id ? "bg-stone-100" : ""}`}>
                    <div className="mb-1 flex items-center justify-between gap-2"><Badge tone={statusTone[c.status]}>{statusLabel(c.status)}</Badge><span className="text-xs text-stone-500">{timeAgo(c.last_message_at)}</span></div>
                    <p className="truncate text-sm text-stone-800">{c.preview || "(no messages)"}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>{selected ? <Detail key={selected} id={selected} onChanged={reload} /> : <EmptyState title="Select a conversation" body="Choose one on the left to read it and reply." />}</Card>
      </div>
    </>
  );
}

export default function Conversations() {
  return <Suspense fallback={<PageLoader />}><Inner /></Suspense>;
}
