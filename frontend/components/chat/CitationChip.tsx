"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import type { SourceCitation } from "@/lib/types/chat";
import { cn } from "@/lib/utils";

type CitationChipProps = {
  source: SourceCitation;
};

export function CitationChip({ source }: CitationChipProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "inline-flex items-center gap-1 rounded-full border border-neutral-700",
          "bg-neutral-800/80 px-2.5 py-1 text-xs text-neutral-300",
          "transition-colors hover:border-neutral-600 hover:bg-neutral-800 hover:text-neutral-100",
        )}
        title={source.excerpt}
      >
        <FileText className="h-3 w-3 shrink-0" />
        <span className="max-w-[180px] truncate">{source.document}</span>
      </button>
      {open && (
        <div
          className={cn(
            "absolute left-0 top-full z-10 mt-1 w-72 rounded-lg border border-neutral-700",
            "bg-neutral-900 p-3 text-xs leading-relaxed text-neutral-300 shadow-lg",
          )}
        >
          <p className="mb-1 font-medium text-neutral-200">{source.document}</p>
          <p className="whitespace-pre-wrap">{source.excerpt}</p>
        </div>
      )}
    </div>
  );
}

type CitationListProps = {
  sources: SourceCitation[];
};

export function CitationList({ sources }: CitationListProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-neutral-800 pt-3">
      <p className="mb-2 text-xs font-medium text-neutral-500">Sources</p>
      <div className="flex flex-wrap gap-2">
        {sources.map((source) => (
          <CitationChip key={source.document} source={source} />
        ))}
      </div>
    </div>
  );
}
