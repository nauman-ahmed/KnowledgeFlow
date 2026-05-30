import { SuggestedPrompts } from "./SuggestedPrompts";

type EmptyStateProps = {
  prompts: readonly string[];
  onSelectPrompt: (prompt: string) => void;
};

export function EmptyState({ prompts, onSelectPrompt }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl space-y-8 text-center">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-100">
            KnowledgeFlow
          </h1>
          <p className="text-neutral-400">Ask anything about the knowledge base</p>
        </div>
        <SuggestedPrompts prompts={prompts} onSelect={onSelectPrompt} />
      </div>
    </div>
  );
}
