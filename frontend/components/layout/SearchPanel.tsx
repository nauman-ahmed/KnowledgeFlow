"use client";

import { FileText, MessageSquare, Search, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSearch } from "@/lib/api/search";
import { useApiAuth } from "@/lib/api/use-api-auth";
import type { SearchResponse } from "@/lib/types/search";
import { cn } from "@/lib/utils";

type SearchPanelProps = {
  onNavigate?: () => void;
};

export function SearchPanel({ onNavigate }: SearchPanelProps) {
  const { getApiToken } = useApiAuth();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const runSearch = useCallback(
    async (value: string) => {
      const trimmed = value.trim();
      if (trimmed.length < 2) {
        setResults(null);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const token = await getApiToken();
        if (!token) {
          setError("Sign in to search");
          return;
        }
        const data = await fetchSearch(trimmed, token);
        setResults(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
        setResults(null);
      } finally {
        setLoading(false);
      }
    },
    [getApiToken],
  );

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runSearch(query);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, runSearch]);

  const hasResults =
    results && (results.documents.length > 0 || results.conversations.length > 0);

  return (
    <div className="px-3 pb-2">
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex w-full items-center gap-2 rounded-lg border border-neutral-700 px-3 py-2 text-sm text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-neutral-200"
        >
          <Search className="h-4 w-4 shrink-0" />
          Search chats & docs
        </button>
      ) : (
        <div className="space-y-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search…"
              className="w-full rounded-lg border border-neutral-600 bg-neutral-900 py-2 pl-8 pr-8 text-sm text-neutral-100 placeholder:text-neutral-500 focus:border-neutral-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setQuery("");
                setResults(null);
                setError(null);
              }}
              className="absolute right-2 top-2 rounded p-0.5 text-neutral-500 hover:text-neutral-300"
              aria-label="Close search"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {loading && (
            <p className="px-1 text-xs text-neutral-500">Searching…</p>
          )}
          {error && <p className="px-1 text-xs text-red-400">{error}</p>}

          {!loading && !error && query.trim().length >= 2 && !hasResults && (
            <p className="px-1 text-xs text-neutral-500">No results</p>
          )}

          {hasResults && (
            <div className="max-h-48 space-y-3 overflow-y-auto rounded-lg border border-neutral-700 bg-neutral-900/50 p-2">
              {results!.conversations.length > 0 && (
                <div>
                  <p className="px-1 pb-1 text-[10px] font-medium uppercase tracking-wide text-neutral-500">
                    Chats
                  </p>
                  <ul className="space-y-0.5">
                    {results!.conversations.map((hit) => (
                      <li key={hit.id}>
                        <Link
                          href={`/chat/${hit.id}`}
                          onClick={onNavigate}
                          className={cn(
                            "flex items-start gap-2 rounded-md px-2 py-1.5 text-xs",
                            "text-neutral-300 hover:bg-neutral-800",
                          )}
                        >
                          <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" />
                          <span className="min-w-0">
                            <span className="block truncate font-medium">{hit.title}</span>
                            <span className="block truncate text-neutral-500">{hit.snippet}</span>
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {results!.documents.length > 0 && (
                <div>
                  <p className="px-1 pb-1 text-[10px] font-medium uppercase tracking-wide text-neutral-500">
                    Documents
                  </p>
                  <ul className="space-y-0.5">
                    {results!.documents.map((hit) => (
                      <li
                        key={hit.id}
                        className="flex items-start gap-2 rounded-md px-2 py-1.5 text-xs text-neutral-400"
                      >
                        <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-500" />
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-neutral-300">
                            {hit.title}
                          </span>
                          <span className="block truncate text-neutral-500">{hit.snippet}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
