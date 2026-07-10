"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { GraphContext } from "@/lib/types/chat";

type GraphDebugPanelProps = {
  graphContext?: GraphContext | null;
};

export function GraphDebugPanel({ graphContext }: GraphDebugPanelProps) {
  const [open, setOpen] = useState(false);

  if (process.env.NODE_ENV !== "development" || !graphContext) {
    return null;
  }

  const hasDetails =
    graphContext.graph_paths?.length ||
    graphContext.cypher_query ||
    graphContext.cypher_error ||
    graphContext.retrieval_mode;

  if (!hasDetails) return null;

  return (
    <div className="mt-3 rounded-lg border border-neutral-800 bg-neutral-900/60">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-neutral-400 hover:text-neutral-200"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        Graph debug
        {graphContext.retrieval_mode ? (
          <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-neutral-500">
            {graphContext.retrieval_mode}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="space-y-3 border-t border-neutral-800 px-3 py-3 text-xs text-neutral-400">
          {graphContext.cypher_query ? (
            <div>
              <p className="mb-1 font-medium text-neutral-500">Cypher</p>
              <pre className="overflow-x-auto rounded bg-neutral-950 p-2 text-[11px] text-neutral-300">
                {graphContext.cypher_query}
              </pre>
            </div>
          ) : null}
          {graphContext.cypher_error ? (
            <p className="text-red-400">Cypher error: {graphContext.cypher_error}</p>
          ) : null}
          {graphContext.graph_paths && graphContext.graph_paths.length > 0 ? (
            <div>
              <p className="mb-1 font-medium text-neutral-500">Graph paths</p>
              <ul className="space-y-1">
                {graphContext.graph_paths.map((path) => (
                  <li key={path} className="rounded bg-neutral-950 px-2 py-1 text-neutral-300">
                    {path}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {typeof graphContext.graph_results_count === "number" ? (
            <p>Cypher rows: {graphContext.graph_results_count}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
