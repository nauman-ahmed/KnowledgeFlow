import { getApiUrl } from "./client";
import type { SourceCitation, StructuredOutput } from "@/lib/types/chat";

export type ChatDonePayload = {
  conversation_id: string;
  message_id: string;
  sources: SourceCitation[];
  structured?: StructuredOutput;
};

export type ChatStreamCallbacks = {
  onToken: (content: string) => void;
  onStep?: (phase: string, message: string) => void;
  onDone: (payload: ChatDonePayload) => void;
  onError: (message: string) => void;
};

export async function streamChat(
  message: string,
  conversationId: string | undefined,
  token: string | null,
  signal: AbortSignal,
  callbacks: ChatStreamCallbacks,
): Promise<void> {
  const response = await fetch(getApiUrl("/api/v1/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? null,
    }),
    signal,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    callbacks.onError(String(detail));
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response stream");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.trim()) continue;

      let eventType = "message";
      let dataLine = "";

      for (const line of part.split("\n")) {
        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLine = line.slice(5).trim();
        }
      }

      if (!dataLine) continue;

      try {
        const data = JSON.parse(dataLine) as Record<string, unknown>;
        if (eventType === "token" && typeof data.content === "string") {
          callbacks.onToken(data.content);
        } else if (eventType === "step" && typeof data.message === "string") {
          callbacks.onStep?.(String(data.phase ?? ""), data.message);
        } else if (eventType === "done") {
          callbacks.onDone(data as unknown as ChatDonePayload);
        } else if (eventType === "error") {
          callbacks.onError(String(data.detail ?? "Stream error"));
        }
      } catch {
        callbacks.onError("Failed to parse stream event");
      }
    }
  }
}
