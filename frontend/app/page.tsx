import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-neutral-950 px-4 text-neutral-100">
      <main className="mx-auto flex w-full max-w-lg flex-col items-center gap-8 text-center">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">KnowledgeFlow</h1>
          <p className="text-neutral-400">
            ChatGPT-style AI assistant over a curated knowledge library. Milestone M0 —
            foundation scaffold.
          </p>
        </div>
        <ul className="flex w-full flex-col gap-3 text-sm">
          <li>
            <Link
              href="/api/health"
              className="block rounded-xl border border-neutral-800 bg-neutral-900 px-4 py-3 transition-colors hover:border-neutral-600"
            >
              Frontend health → <span className="text-neutral-500">/api/health</span>
            </Link>
          </li>
          <li>
            <a
              href="http://localhost:8000/health"
              className="block rounded-xl border border-neutral-800 bg-neutral-900 px-4 py-3 transition-colors hover:border-neutral-600"
            >
              Backend health →{" "}
              <span className="text-neutral-500">http://localhost:8000/health</span>
            </a>
          </li>
        </ul>
        <p className="text-xs text-neutral-600">
          Next: M1 — Clerk auth and ChatGPT-style chat UI per{" "}
          <code className="text-neutral-500">doc/ui_spec.md</code>
        </p>
      </main>
    </div>
  );
}
