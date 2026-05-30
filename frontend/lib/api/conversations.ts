import { apiFetch } from "./client";
import type { ChatMessage, ConversationPreview } from "@/lib/types/chat";

type ConversationSummaryDto = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

type ConversationListDto = {
  conversations: ConversationSummaryDto[];
  total: number;
};

type MessageDto = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { document: string; excerpt: string }[] | null;
  created_at: string;
};

type ConversationDetailDto = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageDto[];
};

function toPreview(dto: ConversationSummaryDto): ConversationPreview {
  return {
    id: dto.id,
    title: dto.title,
    updatedAt: new Date(dto.updated_at),
  };
}

function toMessage(dto: MessageDto): ChatMessage {
  return {
    id: dto.id,
    role: dto.role,
    content: dto.content,
    sources: dto.sources ?? undefined,
  };
}

export async function fetchConversations(token: string | null): Promise<ConversationPreview[]> {
  const data = await apiFetch<ConversationListDto>("/api/v1/conversations", { token });
  return data.conversations.map(toPreview);
}

export async function fetchConversation(
  conversationId: string,
  token: string | null,
): Promise<{ messages: ChatMessage[] }> {
  const data = await apiFetch<ConversationDetailDto>(
    `/api/v1/conversations/${conversationId}`,
    { token },
  );
  return { messages: data.messages.map(toMessage) };
}

export async function deleteConversation(
  conversationId: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`/api/v1/conversations/${conversationId}`, {
    method: "DELETE",
    token,
  });
}
