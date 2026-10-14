"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, FormError, Input, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [f, setF] = useState({ org_name: "", full_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/register", { method: "POST", json: f });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <h1 className="font-serif text-2xl font-semibold">Create your workspace</h1>
      <FormError message={error} />
      <Input label="Business name" required minLength={2} value={f.org_name} onChange={set("org_name")} />
      <Input label="Your name" required value={f.full_name} onChange={set("full_name")} />
      <Input label="Work email" type="email" autoComplete="email" required value={f.email} onChange={set("email")} />
      <Input label="Password" type="password" autoComplete="new-password" required minLength={8} hint="At least 8 characters" value={f.password} onChange={set("password")} />
      <Button type="submit" disabled={busy} className="w-full">{busy && <Spinner />} Create account</Button>
      <p className="text-center text-sm text-stone-500">Already have an account? <Link href="/login" className="font-medium text-teal-800 hover:underline">Sign in</Link></p>
    </form>
  );
}
