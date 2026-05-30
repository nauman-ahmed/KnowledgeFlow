import { apiFetch } from "./client";
import type { SearchResponse } from "@/lib/types/search";

export async function fetchSearch(
  query: string,
  token: string,
  type: "all" | "documents" | "conversations" = "all",
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, type });
  return apiFetch<SearchResponse>(`/api/v1/search?${params.toString()}`, { token });
}
