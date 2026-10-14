import Link from "next/link";

const features = [
  ["Answers grounded in your documents", "Upload PDFs, Word files, text and FAQs. Every answer is retrieved from your own content and cites its source."],
  ["Honest about what it doesn't know", "When the knowledge base has no answer, the agent says so instead of inventing a policy."],
  ["Human handoff built in", "Frustrated customers or repeated misses create a ticket with an AI summary. Your team replies in the same thread."],
  ["Private by design", "Every business is isolated. Passwords are hashed, sessions use HTTP-only cookies, uploads are validated."],
];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="font-serif text-xl font-semibold text-stone-900">Helpdesk<span className="text-teal-800">AI</span></span>
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/login" className="rounded-lg px-3 py-2 font-medium text-stone-700 hover:bg-stone-200/60">Sign in</Link>
          <Link href="/register" className="rounded-lg bg-teal-800 px-4 py-2 font-medium text-white hover:bg-teal-900">Start free</Link>
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-20 pt-12 lg:grid-cols-2">
          <div>
            <p className="mb-4 text-sm font-medium uppercase tracking-widest text-teal-800">AI customer support</p>
            <h1 className="font-serif text-4xl font-semibold leading-tight tracking-tight text-stone-900 sm:text-5xl">
              Support that answers from your handbook, not from its imagination.
            </h1>
            <p className="mt-5 max-w-lg text-lg text-stone-600">
              Turn your documents into a support agent that cites its sources, admits when it&apos;s unsure, and hands the hard conversations to your team.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/register" className="rounded-lg bg-teal-800 px-5 py-3 font-medium text-white hover:bg-teal-900">Create your workspace</Link>
              <Link href="/login" className="rounded-lg border border-stone-300 bg-white px-5 py-3 font-medium text-stone-800 hover:bg-stone-100">Sign in</Link>
            </div>
          </div>

          <div aria-hidden className="rounded-2xl border border-stone-200 bg-white p-5 shadow-xl shadow-stone-300/40">
            <div className="mb-4 flex items-center gap-2 border-b border-stone-100 pb-3">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
              <span className="text-sm font-medium text-stone-700">Support Assistant</span>
            </div>
            <div className="space-y-3 text-sm">
              <p className="ml-auto w-fit max-w-[80%] rounded-2xl rounded-br-sm bg-teal-800 px-4 py-2 text-white">Can I return an opened item?</p>
              <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-stone-100 px-4 py-2 text-stone-800">
                Yes, opened items can be returned within 30 days if they are in working condition [1].
                <p className="mt-2 rounded-md border border-stone-200 bg-white px-2 py-1 text-xs text-stone-500">[1] Returns Policy.pdf · page 2</p>
              </div>
              <p className="ml-auto w-fit max-w-[80%] rounded-2xl rounded-br-sm bg-teal-800 px-4 py-2 text-white">Do you price-match competitors?</p>
              <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-stone-100 px-4 py-2 text-stone-800">
                I couldn&apos;t find that in our knowledge base. Would you like me to connect you with a team member?
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-stone-200 bg-white/60">
          <div className="mx-auto grid max-w-6xl gap-8 px-6 py-16 sm:grid-cols-2">
            {features.map(([t, d]) => (
              <div key={t}>
                <h2 className="font-serif text-xl font-semibold text-stone-900">{t}</h2>
                <p className="mt-2 text-stone-600">{d}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
     
    </div>
  );
}
