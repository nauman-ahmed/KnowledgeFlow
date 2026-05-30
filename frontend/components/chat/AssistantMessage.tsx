import { Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { SourceCitation } from "@/lib/types/chat";
import { CitationList } from "./CitationChip";

type AssistantMessageProps = {
  content: string;
  isStreaming?: boolean;
  sources?: SourceCitation[];
};

export function AssistantMessage({ content, isStreaming, sources }: AssistantMessageProps) {
  return (
    <div className="flex gap-3">
      <div
        className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-800 text-neutral-400"
        aria-hidden
      >
        <Bot className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="prose prose-invert prose-p:my-2 prose-headings:my-3 max-w-none text-[15px] leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          {isStreaming && (
            <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400 align-middle" />
          )}
        </div>
        {!isStreaming && sources && sources.length > 0 && (
          <CitationList sources={sources} />
        )}
      </div>
    </div>
  );
}
