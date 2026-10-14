"use client";
import { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

export function Button({ variant = "primary", className, ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  const styles = {
    primary: "bg-teal-800 text-white hover:bg-teal-900 disabled:bg-teal-800/50",
    secondary: "border border-stone-300 bg-white text-stone-800 hover:bg-stone-100 disabled:opacity-50",
    danger: "bg-red-700 text-white hover:bg-red-800 disabled:opacity-50",
    ghost: "text-stone-600 hover:bg-stone-200/60 disabled:opacity-50",
  }[variant];
  return <button {...p} className={cx("inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-700 focus-visible:ring-offset-2 disabled:cursor-not-allowed", styles, className)} />;
}

const field = "w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-700/20";

export function Input({ label, hint, className, ...p }: InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string }) {
  return (
    <label className="block">
      {label && <span className="mb-1 block text-sm font-medium text-stone-700">{label}</span>}
      <input {...p} className={cx(field, className)} />
      {hint && <span className="mt-1 block text-xs text-stone-500">{hint}</span>}
    </label>
  );
}

export function Textarea({ label, className, ...p }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }) {
  return (
    <label className="block">
      {label && <span className="mb-1 block text-sm font-medium text-stone-700">{label}</span>}
      <textarea {...p} className={cx(field, "resize-none", className)} />
    </label>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-xl border border-stone-200 bg-white shadow-sm", className)}>{children}</div>;
}

const tones = {
  green: "bg-emerald-100 text-emerald-800", amber: "bg-amber-100 text-amber-800", red: "bg-red-100 text-red-800",
  blue: "bg-sky-100 text-sky-800", gray: "bg-stone-200 text-stone-700",
};
export function Badge({ tone = "gray", children }: { tone?: keyof typeof tones; children: ReactNode }) {
  return <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone])}>{children}</span>;
}

export function Spinner({ className }: { className?: string }) {
  return <span role="status" aria-label="Loading" className={cx("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent", className)} />;
}

export function PageLoader() {
  return <div className="flex justify-center py-16 text-teal-800"><Spinner className="h-6 w-6" /></div>;
}

export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-3 h-10 w-10 rounded-full bg-stone-200" aria-hidden />
      <p className="font-medium text-stone-800">{title}</p>
      {body && <p className="mt-1 max-w-sm text-sm text-stone-500">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center rounded-xl border border-red-200 bg-red-50 px-6 py-10 text-center">
      <p className="font-medium text-red-800">Something went wrong</p>
      <p className="mt-1 text-sm text-red-700">{message}</p>
      {onRetry && <Button variant="secondary" className="mt-4" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-serif text-2xl font-semibold tracking-tight text-stone-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-stone-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  return message ? <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p> : null;
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-1 font-serif text-3xl font-semibold text-stone-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-stone-500">{sub}</p>}
    </Card>
  );
}

export const statusTone = { ai_active: "green", escalated: "amber", resolved: "gray", open: "red", in_progress: "amber", ready: "green", processing: "blue", failed: "red" } as const;
export const statusLabel = (s: string) => s.replace("_", " ").replace(/^./, (c) => c.toUpperCase());
