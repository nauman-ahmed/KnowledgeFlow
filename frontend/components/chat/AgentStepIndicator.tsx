"use client";

import { Loader2 } from "lucide-react";

type AgentStepIndicatorProps = {
  message: string | null;
};

export function AgentStepIndicator({ message }: AgentStepIndicatorProps) {
  if (!message) return null;

  return (
    <div className="mx-auto flex max-w-3xl items-center gap-2 px-4 py-2 text-sm text-neutral-400">
      <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
      <span>{message}</span>
    </div>
  );
}
