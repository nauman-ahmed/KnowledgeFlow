import { apiFetch } from "./client";

export type DocumentSummary = {
  id: string;
  title: string;
  filename: string;
  mime_type: string;
  status: string;
  chunk_count: number;
  graph_status?: string | null;
  created_at: string;
  updated_at: string;
};

type DocumentListDto = {
  documents: DocumentSummary[];
  total: number;
};

type DocumentStatsDto = {
  documents_total: number;
  documents_ready: number;
  chunks_total: number;
};

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const data = await apiFetch<DocumentListDto>("/api/v1/documents");
  return data.documents;
}

export async function fetchDocumentStats(): Promise<DocumentStatsDto> {
  return apiFetch<DocumentStatsDto>("/api/v1/documents/stats/summary");
}
