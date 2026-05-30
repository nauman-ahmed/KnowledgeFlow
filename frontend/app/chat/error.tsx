"use client";

export default function ChatError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="text-sm font-medium text-neutral-200">Chat failed to load</p>
      <p className="max-w-md text-xs text-neutral-500">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="rounded-lg border border-neutral-600 px-3 py-1.5 text-xs text-neutral-300 hover:bg-neutral-800"
      >
        Try again
      </button>
    </div>
  );
}
