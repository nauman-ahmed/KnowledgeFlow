"use client";

import { GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

type RelatedConceptChipProps = {
  concept: string;
};

export function RelatedConceptChip({ concept }: RelatedConceptChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-violet-800/80",
        "bg-violet-950/50 px-2.5 py-1 text-xs text-violet-200",
      )}
      title={`Related concept: ${concept}`}
    >
      <GitBranch className="h-3 w-3 shrink-0" />
      <span className="max-w-[180px] truncate">{concept}</span>
    </span>
  );
}

type RelatedConceptListProps = {
  concepts: string[];
};

export function RelatedConceptList({ concepts }: RelatedConceptListProps) {
  if (concepts.length === 0) return null;

  return (
    <div className="mt-3 border-t border-neutral-800 pt-3">
      <p className="mb-2 text-xs font-medium text-neutral-500">Related concepts</p>
      <div className="flex flex-wrap gap-2">
        {concepts.map((concept) => (
          <RelatedConceptChip key={concept} concept={concept} />
        ))}
      </div>
    </div>
  );
}
