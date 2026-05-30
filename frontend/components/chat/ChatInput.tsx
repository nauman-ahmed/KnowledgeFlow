"use client";

import { ArrowUp, Square } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type ChatInputProps = {
  onSend: (message: string) => void;
  onStop?: () => void;
  isGenerating?: boolean;
  disabled?: boolean;
};

export function ChatInput({
  onSend,
  onStop,
  isGenerating = false,
  disabled = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled || isGenerating) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, isGenerating, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div className="border-t border-neutral-800 bg-neutral-900 px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-neutral-700 bg-neutral-800 px-3 py-2 shadow-lg">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Message KnowledgeFlow…"
          rows={1}
          disabled={disabled}
          className="max-h-[200px] min-h-[24px] flex-1 resize-none bg-transparent py-2 text-[15px] text-neutral-100 placeholder:text-neutral-500 focus:outline-none disabled:opacity-50"
        />
        {isGenerating ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            className="mb-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-neutral-600 text-white transition-colors hover:bg-neutral-500"
          >
            <Square className="h-4 w-4 fill-current" />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!value.trim() || disabled}
            aria-label="Send message"
            className={cn(
              "mb-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
              value.trim() && !disabled
                ? "bg-emerald-600 text-white hover:bg-emerald-500"
                : "bg-neutral-700 text-neutral-500 cursor-not-allowed",
            )}
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        )}
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-neutral-600">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
