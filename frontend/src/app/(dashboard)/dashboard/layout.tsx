"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthContext } from "@/components/auth";
import { Button, ErrorState, PageLoader } from "@/components/ui";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Me } from "@/lib/types";

const nav = [
  ["/dashboard", "Overview"],
  ["/dashboard/documents", "Knowledge base"],
  ["/dashboard/conversations", "Conversations"],
  ["/dashboard/tickets", "Tickets"],
  ["/dashboard/analytics", "Analytics"],
  ["/dashboard/settings", "Settings"],
] as const;

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: me, error, reload } = useFetch<Me>("/auth/me");
  const [open, setOpen] = useState(false);

  // UX guard only. The real enforcement is the backend rejecting requests without a valid cookie.
  useEffect(() => { if (error?.status === 401) router.replace("/login"); }, [error, router]);
  useEffect(() => setOpen(false), [pathname]);

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  if (error && error.status !== 401) return <div className="mx-auto max-w-md p-8"><ErrorState message={error.message} onRetry={reload} /></div>;
  if (!me) return <PageLoader />;

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="px-5 py-5">
        <p className="font-serif text-xl font-semibold text-stone-900">Helpdesk<span className="text-teal-800">AI</span></p>
        <p className="mt-1 truncate text-xs text-stone-500">{me.organization.name}</p>
      </div>
      <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
        {nav.map(([href, label]) => {
          const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
          return (
            <Link key={href} href={href} className={`block rounded-lg px-3 py-2 text-sm font-medium ${active ? "bg-teal-800 text-white" : "text-stone-700 hover:bg-stone-200/70"}`}>{label}</Link>
          );
        })}
      </nav>
      <div className="border-t border-stone-200 p-4">
        <p className="truncate text-sm font-medium text-stone-800">{me.user.full_name}</p>
        <p className="mb-3 text-xs capitalize text-stone-500">{me.user.role}</p>
        <Button variant="secondary" className="w-full" onClick={logout}>Sign out</Button>
      </div>
    </div>
  );

  return (
    <AuthContext.Provider value={me}>
      <div className="min-h-screen lg:flex">
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-stone-200 bg-stone-100/70 lg:block">{sidebar}</aside>
        <div className="flex items-center justify-between border-b border-stone-200 bg-stone-100 px-4 py-3 lg:hidden">
          <p className="font-serif text-lg font-semibold">Helpdesk<span className="text-teal-800">AI</span></p>
          <Button variant="secondary" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Toggle menu">Menu</Button>
        </div>
        {open && <div className="border-b border-stone-200 bg-stone-100 lg:hidden">{sidebar}</div>}
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 sm:py-8"><div className="mx-auto max-w-5xl">{children}</div></main>
      </div>
    </AuthContext.Provider>
  );
}
