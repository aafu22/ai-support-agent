import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <Link href="/" className="mb-8 font-serif text-2xl font-semibold text-stone-900">Helpdesk<span className="text-teal-800">AI</span></Link>
      <div className="w-full max-w-sm rounded-2xl border border-stone-200 bg-white p-7 shadow-sm">{children}</div>
    </div>
  );
}
