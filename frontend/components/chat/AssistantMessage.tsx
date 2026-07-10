import { Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { GraphContext, SourceCitation, StructuredOutput } from "@/lib/types/chat";
import { cn } from "@/lib/utils";
import { CitationList } from "./CitationChip";
import { GraphDebugPanel } from "./GraphDebugPanel";
import { RelatedConceptList } from "./RelatedConceptChip";

type AssistantMessageProps = {
  content: string;
  isStreaming?: boolean;
  sources?: SourceCitation[];
  structured?: StructuredOutput;
  graphContext?: GraphContext | null;
};

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-emerald-900/40 text-emerald-300 border-emerald-800",
  medium: "bg-amber-900/40 text-amber-300 border-amber-800",
  low: "bg-neutral-800 text-neutral-400 border-neutral-700",
};

export function AssistantMessage({
  content,
  isStreaming,
  sources,
  structured,
  graphContext,
}: AssistantMessageProps) {
  const displaySources = sources ?? structured?.sources;
  const displayGraphContext = graphContext ?? structured?.graph_context ?? null;
  const relatedConcepts = displayGraphContext?.related_concepts ?? [];
  const confidence = structured?.confidence;
  const keyPoints = structured?.key_points ?? [];

  return (
    <div className="flex gap-3">
      <div
        className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-800 text-neutral-400"
        aria-hidden
      >
        <Bot className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        {!isStreaming && confidence && (
          <div className="mb-2">
            <span
              className={cn(
                "inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
                CONFIDENCE_STYLES[confidence] ?? CONFIDENCE_STYLES.low,
              )}
            >
              {confidence} confidence
            </span>
          </div>
        )}
        <div className="prose prose-invert prose-p:my-2 prose-headings:my-3 max-w-none text-[15px] leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          {isStreaming && (
            <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400 align-middle" />
          )}
        </div>
        {!isStreaming && keyPoints.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-neutral-300">
            {keyPoints.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        )}
        {!isStreaming && displaySources && displaySources.length > 0 && (
          <CitationList sources={displaySources} />
        )}
        {!isStreaming && relatedConcepts.length > 0 && (
          <RelatedConceptList concepts={relatedConcepts} />
        )}
        {!isStreaming && <GraphDebugPanel graphContext={displayGraphContext} />}
      </div>
    </div>
  );
}
