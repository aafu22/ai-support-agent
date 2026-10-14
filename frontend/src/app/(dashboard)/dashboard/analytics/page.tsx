"use client";
import Link from "next/link";
import { Card, EmptyState, ErrorState, PageHeader, PageLoader, Stat } from "@/components/ui";
import { timeAgo, useFetch } from "@/lib/hooks";
import type { Summary, Unanswered } from "@/lib/types";

export default function Analytics() {
  const { data, error, reload } = useFetch<Summary>("/analytics/summary");
  const { data: unanswered } = useFetch<Unanswered[]>("/analytics/unanswered");
  if (error) return <ErrorState message={error.message} onRetry={reload} />;
  if (!data) return <PageLoader />;

  const max = Math.max(1, ...data.conversations_by_day.map((d) => d.count));
  const votes = data.feedback_positive + data.feedback_negative;
  const pct = votes ? Math.round((data.feedback_positive / votes) * 100) : 0;

  return (
    <>
      <PageHeader title="Analytics" subtitle="How the support agent is performing." />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Conversations" value={data.total_conversations} />
        <Stat label="Messages" value={data.total_messages} />
        <Stat label="Resolved" value={data.resolved_conversations} />
        <Stat label="Escalated" value={data.escalated_conversations} />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-serif text-lg font-semibold">Conversations, last 14 days</h2>
          <div className="mt-4 flex h-36 items-end gap-1.5" role="img" aria-label="Bar chart of conversations per day">
            {data.conversations_by_day.map((d) => (
              <div key={d.date} className="group flex h-full flex-1 flex-col justify-end" title={`${d.date}: ${d.count}`}>
                <div className="w-full rounded-t bg-teal-700/80 group-hover:bg-teal-800" style={{ height: `${(d.count / max) * 100}%`, minHeight: d.count ? 4 : 2 }} />
              </div>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-xs text-stone-500"><span>{data.conversations_by_day[0]?.date.slice(5)}</span><span>{data.conversations_by_day.at(-1)?.date.slice(5)}</span></div>
        </Card>
        <Card className="p-5">
          <h2 className="font-serif text-lg font-semibold">Customer feedback</h2>
          {votes === 0 ? <p className="mt-4 text-sm text-stone-500">No ratings yet. Customers can rate each AI answer.</p> : (
            <>
              <p className="mt-3 font-serif text-4xl font-semibold">{pct}%<span className="ml-2 text-sm font-normal text-stone-500">positive</span></p>
              <div className="mt-3 h-3 overflow-hidden rounded-full bg-red-200"><div className="h-full bg-emerald-600" style={{ width: `${pct}%` }} /></div>
              <p className="mt-2 text-sm text-stone-600">{data.feedback_positive} helpful · {data.feedback_negative} not helpful</p>
            </>
          )}
        </Card>
      </div>
      <Card className="mt-6">
        <div className="border-b border-stone-100 p-5">
          <h2 className="font-serif text-lg font-semibold">Unanswered questions ({data.unanswered_questions})</h2>
          <p className="text-sm text-stone-500">Add documents or FAQs covering these to improve the agent.</p>
        </div>
        {!unanswered ? <PageLoader /> : unanswered.length === 0 ? <EmptyState title="Nothing unanswered" body="The agent has answered everything it was asked." /> : (
          <ul className="divide-y divide-stone-100">
            {unanswered.map((u, i) => (
              <li key={i} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                <span className="min-w-0 flex-1 truncate text-stone-800">{u.question}</span>
                <span className="text-xs text-stone-500">{timeAgo(u.created_at)}</span>
                <Link href={`/dashboard/conversations?c=${u.conversation_id}`} className="text-teal-800 hover:underline">View</Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
