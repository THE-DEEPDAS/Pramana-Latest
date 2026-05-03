import Link from 'next/link'
import { ArrowRight, Brain, FileText, Layers3, Search, Sparkles, ShieldCheck, Workflow } from 'lucide-react'

const pillars = [
  {
    icon: Search,
    title: 'Stop searching through files manually',
    description:
      'Teams waste time hunting across PDFs, notes, and presentations. PowerMind is built to turn that scattered content into instant answers.',
  },
  {
    icon: Layers3,
    title: 'Unify context from multiple sources',
    description:
      'Our product keeps documents, visuals, and extracted text together so the answer is grounded in the full context, not just one file.',
  },
  {
    icon: ShieldCheck,
    title: 'Make retrieval reliable and explainable',
    description:
      'Every response is designed to be traceable back to the source material, helping teams trust the system and verify outputs quickly.',
  },
]

const stats = [
  { value: '1 place', label: 'for all document questions' },
  { value: 'Faster', label: 'than manual review workflows' },
  { value: 'Traceable', label: 'answers with source context' },
]

const steps = [
  'Ingest documents and preserve structure.',
  'Retrieve the most relevant passages and visuals.',
  'Generate answers with clear evidence and context.',
]

export default function WhyPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#f5efe4] text-gray-900 dark:bg-[#0b1220] dark:text-gray-100">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,_rgba(246,196,83,0.22),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(59,130,246,0.18),_transparent_28%),linear-gradient(180deg,_#f5efe4_0%,_#fbf6ec_100%)] dark:bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.22),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(37,99,235,0.18),_transparent_28%),linear-gradient(180deg,_#0b1220_0%,_#10192c_100%)]" />

      <section className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-8 lg:px-10">
        <div className="mb-8 flex items-center justify-between rounded-2xl border border-[#e3d5bf] bg-white/70 px-5 py-4 shadow-[0_12px_40px_rgba(0,0,0,0.06)] backdrop-blur dark:border-[#22314f] dark:bg-[#10192c]/80">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-[#f6c453] to-[#e5ae37] text-gray-900 shadow-lg shadow-amber-500/25 dark:from-[#3b82f6] dark:to-[#1d4ed8] dark:text-white dark:shadow-blue-500/20">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-800 dark:text-blue-200">PowerMind</p>
              <p className="text-sm text-gray-600 dark:text-blue-100/70">Why we built this product</p>
            </div>
          </div>

          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#f6c453] to-[#e5ae37] px-4 py-2 text-sm font-semibold text-gray-900 shadow-lg shadow-amber-500/20 transition-all hover:from-[#f8cd68] hover:to-[#eab843] dark:from-[#3b82f6] dark:to-[#2563eb] dark:text-white dark:shadow-blue-500/20 dark:hover:from-[#4f8cf7] dark:hover:to-[#1d4ed8]"
          >
            Open product
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid flex-1 gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#ead8b0] bg-[#fff4dc] px-4 py-2 text-sm font-medium text-amber-800 dark:border-[#24406e] dark:bg-[#13213f] dark:text-blue-100">
              <Sparkles className="h-4 w-4" />
              Built for teams that live in documents
            </div>

            <div className="space-y-5">
              <h1 className="max-w-3xl text-5xl font-bold tracking-tight text-gray-900 dark:text-gray-50 sm:text-6xl">
                We built PowerMind so people can ask questions, not hunt for answers.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-gray-600 dark:text-blue-100/75">
                The product exists to remove the friction between information and action. Instead of manually opening PDFs,
                checking decks, and cross-referencing notes, PowerMind brings the right context forward in one place.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/"
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#f6c453] to-[#e5ae37] px-5 py-3 text-sm font-semibold text-gray-900 shadow-lg shadow-amber-500/25 transition-all hover:from-[#f8cd68] hover:to-[#eab843] dark:from-[#3b82f6] dark:to-[#2563eb] dark:text-white dark:shadow-blue-500/20 dark:hover:from-[#4f8cf7] dark:hover:to-[#1d4ed8]"
              >
                Launch the chatbot
                <ArrowRight className="h-4 w-4" />
              </Link>

              <a
                href="#details"
                className="inline-flex items-center gap-2 rounded-xl border border-[#ddcfb9] bg-white/70 px-5 py-3 text-sm font-semibold text-gray-800 shadow-sm transition-all hover:bg-[#fff7e7] dark:border-[#24406e] dark:bg-[#13213f]/80 dark:text-blue-50 dark:hover:bg-[#173059]"
              >
                View the reasoning
              </a>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {stats.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-[#e2d6c1] bg-white/75 p-5 shadow-[0_10px_30px_rgba(0,0,0,0.05)] backdrop-blur dark:border-[#22314f] dark:bg-[#10192c]/80"
                >
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-50">{stat.value}</p>
                  <p className="mt-1 text-sm text-gray-600 dark:text-blue-100/70">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-0 -z-10 rounded-[2rem] bg-gradient-to-br from-[#f9e7b2] to-[#f3d27a] blur-3xl opacity-60 dark:from-[#1e3a8a] dark:to-[#0f172a] dark:opacity-80" />
            <div className="rounded-[2rem] border border-[#e1d4bd] bg-white/80 p-6 shadow-[0_18px_60px_rgba(0,0,0,0.08)] backdrop-blur dark:border-[#22314f] dark:bg-[#10192c]/90">
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#fff4dc] text-amber-700 dark:bg-[#13213f] dark:text-blue-200">
                  <FileText className="h-6 w-6" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900 dark:text-gray-50">Why this matters</p>
                  <p className="text-sm text-gray-600 dark:text-blue-100/70">A product people can trust in real workflows</p>
                </div>
              </div>

              <div className="space-y-4" id="details">
                {pillars.map((pillar) => (
                  <div
                    key={pillar.title}
                    className="rounded-2xl border border-[#e7dcc8] bg-[#fffaf1] p-4 dark:border-[#24406e] dark:bg-[#13213f]"
                  >
                    <div className="mb-2 flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fff0ca] text-amber-800 dark:bg-[#173059] dark:text-blue-100">
                        <pillar.icon className="h-5 w-5" />
                      </div>
                      <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50">{pillar.title}</h2>
                    </div>
                    <p className="text-sm leading-6 text-gray-600 dark:text-blue-100/70">{pillar.description}</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-2xl border border-[#e4d6be] bg-gradient-to-r from-[#fff4dc] to-[#f8e3b0] p-5 dark:border-[#24406e] dark:from-[#13213f] dark:to-[#10192c]">
                <div className="flex items-start gap-3">
                  <Workflow className="mt-0.5 h-5 w-5 text-amber-700 dark:text-blue-300" />
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-gray-50">How it works</p>
                    <ol className="mt-3 space-y-2 text-sm text-gray-700 dark:text-blue-100/75">
                      {steps.map((step, index) => (
                        <li key={step} className="flex gap-3">
                          <span className="inline-flex h-6 w-6 flex-none items-center justify-center rounded-full bg-amber-500 text-xs font-bold text-gray-900 dark:bg-[#3b82f6] dark:text-white">
                            {index + 1}
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}