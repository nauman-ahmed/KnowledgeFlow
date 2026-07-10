"use client";

import { Loader2, Network, Search, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

type AgentStepIndicatorProps = {
  message: string | null;
  phase?: string | null;
};

const PHASE_ICONS: Record<string, typeof Search> = {
  planner: Sparkles,
  researcher: Search,
  graph_researcher: Network,
  cypher_generator: Network,
  answer_generator: Sparkles,
  guardrails: Sparkles,
};

export function AgentStepIndicator({ message, phase }: AgentStepIndicatorProps) {
  if (!message) return null;

  const Icon = (phase && PHASE_ICONS[phase]) || Loader2;
  const spinning = Icon === Loader2;

  return (
    <div className="mx-auto flex max-w-3xl items-center gap-2 px-4 py-2 text-sm text-neutral-400">
      <Icon className={cn("h-4 w-4 shrink-0", spinning && "animate-spin")} />
      <span>{message}</span>
    </div>
  );
}
