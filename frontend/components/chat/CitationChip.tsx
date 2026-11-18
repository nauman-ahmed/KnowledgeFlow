"use client";

import { useEffect, useRef, useState } from "react";
import { FileText } from "lucide-react";
import type { SourceCitation } from "@/lib/types/chat";
import { cn } from "@/lib/utils";

type CitationChipProps = {
  source: SourceCitation;
};

/** Roughly the popover's height (w-72, max-h-60 + padding). */
const POPOVER_SPACE_PX = 260;

/** Bottom edge of the nearest scrolling ancestor, which clips the popover. */
function clipBottom(el: HTMLElement): number {
  let node = el.parentElement;
  while (node) {
    const { overflowY } = window.getComputedStyle(node);
    if (overflowY === "auto" || overflowY === "scroll" || overflowY === "hidden") {
      return node.getBoundingClientRect().bottom;
    }
    node = node.parentElement;
  }
  return window.innerHeight;
}

export function CitationChip({ source }: CitationChipProps) {
  const [open, setOpen] = useState(false);
  const [openUp, setOpenUp] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  function toggle() {
    const root = rootRef.current;
    if (!open && root) {
      // Near the bottom of the chat the popover would be cut off; open it upwards.
      setOpenUp(clipBottom(root) - root.getBoundingClientRect().bottom < POPOVER_SPACE_PX);
    }
    setOpen((v) => !v);
  }

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative inline-block">
      <button
        type="button"
        aria-expanded={open}
        onClick={toggle}
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
            "absolute left-0 z-10 max-h-60 w-72 overflow-y-auto rounded-lg border border-neutral-700",
            "bg-neutral-900 p-3 text-xs leading-relaxed text-neutral-300 shadow-lg",
            openUp ? "bottom-full mb-1" : "top-full mt-1",
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
        {/* One document can be cited several times with different excerpts. */}
        {sources.map((source, index) => (
          <CitationChip key={`${source.document}-${index}`} source={source} />
        ))}
      </div>
    </div>
  );
}
