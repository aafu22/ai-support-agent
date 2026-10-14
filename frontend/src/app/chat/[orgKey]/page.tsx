"use client";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatReply, Msg, PublicConversation, Source } from "@/lib/types";

interface Config { organization_name: string; bot_name: string; greeting: string }
type Rated = Record<string, "up" | "down">;

function randomId(): string {
  const a = new Uint8Array(16);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

export default function CustomerChat() {
  const { orgKey } = useParams<{ orgKey: string }>();
  const storeKey = `helpdesk:${orgKey}`;
  const [config, setConfig] = useState<Config | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [session, setSession] = useState<string>("");
  const [convId, setConvId] = useState<string | null>(null);
  const [status, setStatus] = useState("ai_active");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rated, setRated] = useState<Rated>({});
  const [email, setEmail] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  // Restore anonymous session + conversation from this browser.
  useEffect(() => {
    let s = "", c: string | null = null;
    try {
      const saved = JSON.parse(localStorage.getItem(storeKey) ?? "{}");
      s = saved.session || randomId();
      c = saved.conversation ?? null;
      localStorage.setItem(storeKey, JSON.stringify({ session: s, conversation: c }));
    } catch { s = randomId(); }
    setSession(s); setConvId(c);
    api<Config>(`/public/config?public_key=${encodeURIComponent(orgKey)}`).then(setConfig).catch((e) => setFatal(e.status === 404 ? "This support chat doesn't exist." : "Support chat is unavailable right now."));
  }, [orgKey, storeKey]);

  const load = useCallback(async () => {
    if (!convId || !session) return;
    try {
      const d = await api<PublicConversation>(`/public/conversations/${convId}?public_key=${encodeURIComponent(orgKey)}&session_id=${session}`);
      setMessages(d.messages); setStatus(d.status);
    } catch (e) {
      if ((e as { status?: number }).status === 404) { // stale conversation id
        localStorage.setItem(storeKey, JSON.stringify({ session, conversation: null })); setConvId(null); setMessages([]);
      }
    }
  }, [convId, session, orgKey, storeKey]);

  useEffect(() => { load(); }, [load]);
  // While a human is handling the chat, poll for their replies.
  useEffect(() => {
    if (status !== "escalated") return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [status, load]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages.length, sending]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const content = text.trim();
    if (!content || sending) return;
    setText(""); setError(null); setSending(true);
    setMessages((m) => [...m, { id: `tmp-${Date.now()}`, role: "customer", content, sources: null, created_at: new Date().toISOString() }]);
    try {
      const r = await api<ChatReply>("/public/chat", { method: "POST", json: { public_key: orgKey, session_id: session, message: content, conversation_id: convId } });
      setStatus(r.status);
      if (!convId) {
        // New conversation: setting the id triggers the load effect, which replaces the temp message.
        localStorage.setItem(storeKey, JSON.stringify({ session, conversation: r.conversation_id }));
        setConvId(r.conversation_id);
      } else {
        await load();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send message");
      setMessages((m) => m.filter((x) => !x.id.startsWith("tmp-")));
      setText(content);
    } finally { setSending(false); }
  }

  async function rate(id: string, rating: "up" | "down") {
    setRated((r) => ({ ...r, [id]: rating }));
    try { await api(`/public/messages/${id}/feedback`, { method: "POST", json: { public_key: orgKey, session_id: session, rating } }); } catch {}
  }

  async function escalate(withEmail?: string) {
    if (!convId) return;
    try {
      await api("/public/escalate", { method: "POST", json: { public_key: orgKey, session_id: session, conversation_id: convId, email: withEmail || null } });
      if (withEmail) setEmailSent(true);
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not reach support"); }
  }

  if (fatal) return <div className="flex min-h-screen items-center justify-center p-6 text-center text-stone-600">{fatal}</div>;
  if (!config) return <div className="flex min-h-screen items-center justify-center text-stone-500">Loading…</div>;

  const escalated = status === "escalated";
  const lastIsHuman = [...messages].reverse().find((m) => m.role !== "customer")?.role === "human_agent";

  return (
    <div className="mx-auto flex h-dvh max-w-2xl flex-col bg-white shadow-xl sm:my-0 sm:border-x sm:border-stone-200">
      <header className="flex items-center gap-3 border-b border-stone-200 bg-teal-800 px-5 py-4 text-white">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15 font-serif text-lg">{config.bot_name[0]}</div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{config.organization_name}</p>
          <p className="text-xs text-teal-100">{escalated ? "A team member will reply here" : `${config.bot_name} · AI assistant`}</p>
        </div>
        {!escalated && convId && <button onClick={() => escalate()} className="rounded-lg border border-white/30 px-3 py-1.5 text-xs font-medium hover:bg-white/10">Talk to a human</button>}
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto bg-stone-50 px-4 py-5" aria-live="polite">
        <Bubble role="assistant" content={config.greeting} />
        {messages.map((m) => (
          <div key={m.id}>
            <Bubble role={m.role} content={m.content} label={m.role === "human_agent" ? "Support team" : undefined} />
            {m.role === "assistant" && m.sources && m.sources.length > 0 && <Sources sources={m.sources} />}
            {m.role === "assistant" && !m.id.startsWith("tmp-") && !m.id.startsWith("a-") && (
              <div className="ml-1 mt-1 flex items-center gap-1 text-xs text-stone-400">
                {(["up", "down"] as const).map((r) => (
                  <button key={r} onClick={() => rate(m.id, r)} disabled={!!rated[m.id]} aria-label={r === "up" ? "Helpful" : "Not helpful"}
                    className={`rounded px-1.5 py-0.5 hover:bg-stone-200 ${rated[m.id] === r ? "bg-stone-200 text-stone-800" : ""}`}>{r === "up" ? "👍" : "👎"}</button>
                ))}
                {rated[m.id] && <span>Thanks for the feedback</span>}
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="flex w-fit gap-1 rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-sm" aria-label="Assistant is typing">
            {[0, 1, 2].map((i) => <span key={i} className="dot h-2 w-2 rounded-full bg-stone-400" style={{ animationDelay: `${i * 0.15}s` }} />)}
          </div>
        )}
        {escalated && !lastIsHuman && !emailSent && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <p className="mb-2">Leave your email so we can reach you if you close this page (optional).</p>
            <form onSubmit={(e) => { e.preventDefault(); if (email) escalate(email); }} className="flex gap-2">
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" aria-label="Your email" className="min-w-0 flex-1 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm" />
              <button className="rounded-lg bg-amber-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-800">Send</button>
            </form>
          </div>
        )}
        {emailSent && <p className="text-center text-xs text-stone-500">Thanks. We have your email.</p>}
        <div ref={end} />
      </div>

      {error && <p role="alert" className="border-t border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}
      <form onSubmit={send} className="flex gap-2 border-t border-stone-200 bg-white p-3">
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} placeholder={escalated ? "Message our support team…" : "Type your question…"} aria-label="Your message"
          className="min-w-0 flex-1 rounded-xl border border-stone-300 px-4 py-2.5 text-sm focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-700/20" />
        <button disabled={sending || !text.trim()} className="rounded-xl bg-teal-800 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-900 disabled:bg-teal-800/40">Send</button>
      </form>
      <p className="bg-white pb-2 text-center text-[11px] text-stone-400">AI answers may contain mistakes. Check important details with our team.</p>
    </div>
  );
}

function Bubble({ role, content, label }: { role: Msg["role"]; content: string; label?: string }) {
  const mine = role === "customer";
  return (
    <div className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
      {label && <span className="mb-0.5 ml-1 text-xs font-medium text-amber-800">{label}</span>}
      <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${mine ? "rounded-br-sm bg-teal-800 text-white" : role === "human_agent" ? "rounded-bl-sm bg-amber-100 text-amber-950" : "rounded-bl-sm bg-white text-stone-800"}`}>{content}</div>
    </div>
  );
}

function Sources({ sources }: { sources: Source[] }) {
  return (
    <details className="ml-1 mt-1.5 max-w-[85%] text-xs text-stone-500">
      <summary className="cursor-pointer select-none font-medium text-teal-800">Sources ({sources.length})</summary>
      <ul className="mt-1 space-y-1.5">
        {sources.map((s) => (
          <li key={s.id} className="rounded-lg border border-stone-200 bg-white px-2.5 py-1.5">
            <span className="font-medium text-stone-700">[{s.id}] {s.title}{s.page ? ` · page ${s.page}` : ""}</span>
            <p className="mt-0.5 line-clamp-2">{s.snippet}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}
