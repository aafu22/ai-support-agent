"use client";
import { useRef, useState } from "react";
import { useAuth } from "@/components/auth";
import { Badge, Button, Card, EmptyState, ErrorState, FormError, Input, PageHeader, PageLoader, Spinner, Textarea, statusLabel, statusTone } from "@/components/ui";
import { api } from "@/lib/api";
import { timeAgo, useFetch } from "@/lib/hooks";
import type { Doc } from "@/lib/types";

const size = (b: number) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

export default function Documents() {
  const { user } = useAuth();
  const isOwner = user.role === "owner";
  const [inputKey, setInputKey] = useState(0);
  const { data, error, reload } = useFetch<Doc[]>("/documents", 3000); // polls so status updates appear on their own
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [showFaq, setShowFaq] = useState(false);
  const [faq, setFaq] = useState({ title: "", items: [{ question: "", answer: "" }] });
  const [faqBusy, setFaqBusy] = useState(false);

  async function upload(file: File) {
    setUploading(true); setMsg(null);
    const form = new FormData();
    form.append("file", file);
    try { await api("/documents", { method: "POST", form }); await reload(); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Upload failed"); }
    finally { setUploading(false); setInputKey((k) => k + 1); }
  }

  async function saveFaq(e: React.FormEvent) {
    e.preventDefault(); setFaqBusy(true); setMsg(null);
    try {
      await api("/documents/faq", { method: "POST", json: faq });
      setFaq({ title: "", items: [{ question: "", answer: "" }] }); setShowFaq(false); await reload();
    } catch (err) { setMsg(err instanceof Error ? err.message : "Could not save FAQ"); }
    finally { setFaqBusy(false); }
  }

  async function remove(d: Doc) {
    if (!confirm(`Delete "${d.title}"? The agent will stop using it.`)) return;
    try { await api(`/documents/${d.id}`, { method: "DELETE" }); await reload(); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Delete failed"); }
  }

  const setItem = (i: number, k: "question" | "answer", v: string) =>
    setFaq({ ...faq, items: faq.items.map((it, n) => (n === i ? { ...it, [k]: v } : it)) });

  return (
    <>
      <PageHeader
        title="Knowledge base"
        subtitle="The agent answers only from what you add here."
        action={isOwner && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setShowFaq(!showFaq)}>Add FAQ</Button>
            <Button onClick={() => fileRef.current?.click()} disabled={uploading}>{uploading && <Spinner />} Upload file</Button>
            <input key={inputKey} ref={fileRef} type="file" hidden accept=".pdf,.docx,.txt" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          </div>
        )}
      />
      <div className="space-y-4">
        <FormError message={msg} />
        {showFaq && (
          <Card className="p-5">
            <form onSubmit={saveFaq} className="space-y-4">
              <Input label="FAQ set name" placeholder="e.g. Shipping & returns" required value={faq.title} onChange={(e) => setFaq({ ...faq, title: e.target.value })} />
              {faq.items.map((it, i) => (
                <div key={i} className="space-y-2 rounded-lg bg-stone-50 p-3">
                  <Input label={`Question ${i + 1}`} required minLength={3} value={it.question} onChange={(e) => setItem(i, "question", e.target.value)} />
                  <Textarea label="Answer" rows={2} required value={it.answer} onChange={(e) => setItem(i, "answer", e.target.value)} />
                </div>
              ))}
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="ghost" onClick={() => setFaq({ ...faq, items: [...faq.items, { question: "", answer: "" }] })}>+ Another question</Button>
                <Button type="submit" disabled={faqBusy}>{faqBusy && <Spinner />} Save FAQ</Button>
              </div>
            </form>
          </Card>
        )}
        {error ? <ErrorState message={error.message} onRetry={reload} /> : !data ? <PageLoader /> : data.length === 0 ? (
          <Card><EmptyState title="No knowledge yet" body="Upload a PDF, DOCX or TXT file (max 10 MB), or add FAQs. Processing takes a few seconds." /></Card>
        ) : (
          <Card className="divide-y divide-stone-100">
            {data.map((d) => (
              <div key={d.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-stone-900">{d.title}</p>
                  <p className="text-xs text-stone-500">{(d.file_type ?? "").toUpperCase()} · {size(d.file_size)} · {d.status === "ready" ? `${d.chunk_count} chunks · ` : ""}{timeAgo(d.created_at)}</p>
                  {d.error_message && <p className="mt-1 text-xs text-red-700">{d.error_message}</p>}
                </div>
                <Badge tone={statusTone[d.status]}>{d.status === "processing" && <Spinner className="mr-1.5 h-3 w-3" />}{statusLabel(d.status)}</Badge>
                {isOwner && <Button variant="ghost" onClick={() => remove(d)} aria-label={`Delete ${d.title}`}>Delete</Button>}
              </div>
            ))}
          </Card>
        )}
      </div>
    </>
  );
}
