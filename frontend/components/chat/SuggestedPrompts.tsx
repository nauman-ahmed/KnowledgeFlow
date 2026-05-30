type SuggestedPromptsProps = {
  prompts: readonly string[];
  onSelect: (prompt: string) => void;
};

export function SuggestedPrompts({ prompts, onSelect }: SuggestedPromptsProps) {
  return (
    <div className="grid w-full gap-2">
      {prompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onSelect(prompt)}
          className="rounded-xl border border-neutral-700 bg-neutral-800/50 px-4 py-3 text-left text-sm text-neutral-200 transition-colors hover:border-neutral-600 hover:bg-neutral-800"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
