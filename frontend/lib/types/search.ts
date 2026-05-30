export type DocumentSearchHit = {
  id: string;
  title: string;
  filename: string;
  snippet: string;
  score: number;
};

export type ConversationSearchHit = {
  id: string;
  title: string;
  snippet: string;
  updated_at: string;
};

export type SearchResponse = {
  query: string;
  documents: DocumentSearchHit[];
  conversations: ConversationSearchHit[];
};
