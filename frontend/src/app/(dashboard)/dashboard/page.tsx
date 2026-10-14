"use client";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth";
import { Button, Card, ErrorState, PageHeader, PageLoader, Stat } from "@/components/ui";
import { useFetch } from "@/lib/hooks";
import type { Doc, Summary } from "@/lib/types";

export default function Overview() {
  const { organization, user } = useAuth();
  const { data, error, reload } = useFetch<Summary>("/analytics/summary");
  const { data: docs } = useFetch<Doc[]>("/documents");
  const [copied, setCopied] = useState(false);
  const link = typeof window === "undefined" ? "" : `${window.location.origin}/chat/${organization.public_key}`;
  const ready = docs?.filter((d) => d.status === "ready").length ?? 0;

  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return <PageLoader />;

  return (
    <>
      <PageHeader title={`Welcome, ${user.full_name.split(" ")[0]}`} subtitle="Here is how your support is doing." />
      {docs && ready === 0 && (
        <Card className="mb-6 border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Your agent has no knowledge yet. <Link href="/dashboard/documents" className="font-medium underline">Add a document or FAQ</Link> so it can start answering.
        </Card>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Conversations" value={data.total_conversations} />
        <Stat label="Open tickets" value={data.open_tickets} />
        <Stat label="Unanswered" value={data.unanswered_questions} sub="Questions the AI couldn't answer" />
        <Stat label="Knowledge sources" value={ready} />
      </div>
      <Card className="mt-6 p-5">
        <h2 className="font-serif text-lg font-semibold">Your customer chat link</h2>
        <p className="mt-1 text-sm text-stone-500">Share this page with customers, or link to it from your website.</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-lg bg-stone-100 px-3 py-2 text-sm">{link}</code>
          <Button variant="secondary" onClick={async () => { await navigator.clipboard.writeText(link); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? "Copied" : "Copy"}</Button>
          <a href={link} target="_blank" rel="noreferrer"><Button>Open chat</Button></a>
        </div>
      </Card>
    </>
  );
}
