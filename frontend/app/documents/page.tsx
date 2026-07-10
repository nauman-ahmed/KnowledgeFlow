"use client";

import { FileText } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchDocumentStats, fetchDocuments, type DocumentSummary } from "@/lib/api/documents";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  ready: "bg-emerald-900/40 text-emerald-300 border-emerald-800",
  processing: "bg-amber-900/40 text-amber-300 border-amber-800",
  error: "bg-red-900/40 text-red-300 border-red-800",
  pending: "bg-neutral-800 text-neutral-400 border-neutral-700",
};

const GRAPH_STYLES: Record<string, string> = {
  extracted: "text-violet-300",
  pending: "text-neutral-500",
  failed: "text-red-400",
  skipped: "text-neutral-500",
};

function DocumentRow({ document }: { document: DocumentSummary }) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-neutral-800 text-neutral-400">
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-medium text-neutral-100">{document.title}</h2>
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide",
                STATUS_STYLES[document.status] ?? STATUS_STYLES.pending,
              )}
            >
              {document.status}
            </span>
          </div>
          <p className="mt-1 truncate text-xs text-neutral-500">{document.filename}</p>
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-neutral-400">
            <span>{document.chunk_count} chunks</span>
            {document.graph_status ? (
              <span className={GRAPH_STYLES[document.graph_status] ?? "text-neutral-500"}>
                graph: {document.graph_status}
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [stats, setStats] = useState<{ documents_total: number; documents_ready: number; chunks_total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [docs, summary] = await Promise.all([fetchDocuments(), fetchDocumentStats()]);
        if (!cancelled) {
          setDocuments(docs);
          setStats(summary);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load documents");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-neutral-100">Knowledge library</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Curated documents indexed for vector search and graph extraction.
          </p>
        </div>

        {stats ? (
          <div className="mb-6 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
              <p className="text-xs text-neutral-500">Documents</p>
              <p className="mt-1 text-2xl font-semibold text-neutral-100">{stats.documents_total}</p>
            </div>
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
              <p className="text-xs text-neutral-500">Ready</p>
              <p className="mt-1 text-2xl font-semibold text-neutral-100">{stats.documents_ready}</p>
            </div>
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
              <p className="text-xs text-neutral-500">Chunks</p>
              <p className="mt-1 text-2xl font-semibold text-neutral-100">{stats.chunks_total}</p>
            </div>
          </div>
        ) : null}

        {loading ? (
          <p className="text-sm text-neutral-500">Loading documents…</p>
        ) : error ? (
          <p className="text-sm text-red-400">{error}</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-neutral-500">No documents ingested yet.</p>
        ) : (
          <div className="space-y-3">
            {documents.map((document) => (
              <DocumentRow key={document.id} document={document} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
