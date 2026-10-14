"use client";
import { useState } from "react";
import { useAuth } from "@/components/auth";
import { Badge, Button, Card, FormError, Input, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Org, User } from "@/lib/types";

export default function Settings() {
  const { organization, user } = useAuth();
  const isOwner = user.role === "owner";
  const s = organization.settings;
  const [f, setF] = useState({ name: organization.name, bot_name: s.bot_name ?? "", greeting: s.greeting ?? "", support_email: s.support_email ?? "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const { data: team, reload } = useFetch<User[]>("/team");
  const [agent, setAgent] = useState({ full_name: "", email: "", password: "" });
  const [agentMsg, setAgentMsg] = useState<string | null>(null);
  const link = typeof window === "undefined" ? "" : `${window.location.origin}/chat/${organization.public_key}`;

  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setMsg(null);
    try {
      await api<Org>("/organization", { method: "PATCH", json: { ...f, support_email: f.support_email || null } });
      setMsg({ ok: true, text: "Saved. Customers see the changes immediately." });
    } catch (err) { setMsg({ ok: false, text: err instanceof Error ? err.message : "Save failed" }); }
    finally { setBusy(false); }
  }

  async function addAgent(e: React.FormEvent) {
    e.preventDefault(); setAgentMsg(null);
    try { await api("/team", { method: "POST", json: agent }); setAgent({ full_name: "", email: "", password: "" }); await reload(); }
    catch (err) { setAgentMsg(err instanceof Error ? err.message : "Could not add agent"); }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="Branding for your customer chat and your support team." />
      <div className="space-y-6">
        <Card className="p-5">
          <form onSubmit={save} className="space-y-4">
            <h2 className="font-serif text-lg font-semibold">Organization & chat</h2>
            <FormError message={msg && !msg.ok ? msg.text : null} />
            {msg?.ok && <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{msg.text}</p>}
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Business name" disabled={!isOwner} required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
              <Input label="Assistant name" disabled={!isOwner} required value={f.bot_name} onChange={(e) => setF({ ...f, bot_name: e.target.value })} />
            </div>
            <Input label="Greeting message" disabled={!isOwner} required maxLength={300} value={f.greeting} onChange={(e) => setF({ ...f, greeting: e.target.value })} />
            <Input label="Support email (optional)" type="email" disabled={!isOwner} value={f.support_email} onChange={(e) => setF({ ...f, support_email: e.target.value })} />
            {isOwner ? <Button type="submit" disabled={busy}>{busy && <Spinner />} Save changes</Button> : <p className="text-sm text-stone-500">Only the owner can change settings.</p>}
          </form>
        </Card>
        <Card className="p-5">
          <h2 className="font-serif text-lg font-semibold">Public chat link</h2>
          <code className="mt-2 block truncate rounded-lg bg-stone-100 px-3 py-2 text-sm">{link}</code>
        </Card>
        <Card className="p-5">
          <h2 className="font-serif text-lg font-semibold">Team</h2>
          <ul className="mt-3 divide-y divide-stone-100">
            {team?.map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2 text-sm">
                <span>{u.full_name} <span className="text-stone-500">· {u.email}</span></span>
                <Badge tone={u.role === "owner" ? "blue" : "gray"}>{u.role}</Badge>
              </li>
            ))}
          </ul>
          {isOwner && (
            <form onSubmit={addAgent} className="mt-4 space-y-3 border-t border-stone-100 pt-4">
              <p className="text-sm font-medium">Add a support agent</p>
              <FormError message={agentMsg} />
              <div className="grid gap-3 sm:grid-cols-3">
                <Input aria-label="Agent name" placeholder="Full name" required value={agent.full_name} onChange={(e) => setAgent({ ...agent, full_name: e.target.value })} />
                <Input aria-label="Agent email" type="email" placeholder="Email" required value={agent.email} onChange={(e) => setAgent({ ...agent, email: e.target.value })} />
                <Input aria-label="Temporary password" type="password" placeholder="Temporary password" minLength={8} required value={agent.password} onChange={(e) => setAgent({ ...agent, password: e.target.value })} />
              </div>
              <Button type="submit" variant="secondary">Add agent</Button>
              <p className="text-xs text-stone-500">Agents can handle conversations and tickets but cannot manage documents or settings.</p>
            </form>
          )}
        </Card>
      </div>
    </>
  );
}
