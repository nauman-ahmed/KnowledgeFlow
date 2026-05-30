"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat } from "@/lib/api/chat";
import { fetchConversation } from "@/lib/api/conversations";
import { useApiAuth } from "@/lib/api/use-api-auth";
import { SUGGESTED_PROMPTS, type ChatMessage } from "@/lib/types/chat";
import { ChatInput } from "./ChatInput";
import { ChatThread } from "./ChatThread";
import { EmptyState } from "./EmptyState";

type ChatViewProps = {
  conversationId?: string;
  initialMessages?: ChatMessage[];
};

function createId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatView({ conversationId, initialMessages = [] }: ChatViewProps) {
  const router = useRouter();
  const { isAuthReady, getApiToken } = useApiAuth();
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(Boolean(conversationId && initialMessages.length === 0));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!conversationId || initialMessages.length > 0 || !isAuthReady) return;

    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const token = await getApiToken();
        if (!token) {
          if (!cancelled) setLoadError("Not signed in");
          return;
        }
        const data = await fetchConversation(conversationId!, token);
        if (!cancelled) {
          setMessages(data.messages);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Failed to load conversation");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [conversationId, initialMessages.length, getApiToken, isAuthReady]);

  const appendExchange = useCallback(
    async (userText: string) => {
      const userMsg: ChatMessage = { id: createId(), role: "user", content: userText };
      const assistantId = createId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsGenerating(true);
      setStreamingId(assistantId);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const token = await getApiToken();
        if (!token) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: "Error: Not signed in. Please refresh and try again." }
                : m,
            ),
          );
          return;
        }
        await streamChat(
          userText,
          conversationId,
          token,
          controller.signal,
          {
            onToken: (content) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: m.content + content } : m,
                ),
              );
            },
            onDone: (payload) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        id: payload.message_id,
                        sources: payload.sources,
                      }
                    : m,
                ),
              );
              if (!conversationId) {
                router.replace(`/chat/${payload.conversation_id}`);
              }
            },
            onError: (message) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content || `Error: ${message}` }
                    : m,
                ),
              );
            },
          },
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content || "Something went wrong. Please try again." }
                : m,
            ),
          );
        }
      } finally {
        abortRef.current = null;
        setIsGenerating(false);
        setStreamingId(null);
      }
    },
    [conversationId, getApiToken, router],
  );

  const handleSend = useCallback(
    (text: string) => {
      if (isGenerating || isLoading) return;
      void appendExchange(text);
    },
    [appendExchange, isGenerating, isLoading],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsGenerating(false);
    setStreamingId(null);
  }, []);

  const showEmpty = messages.length === 0 && !isLoading && !loadError;

  return (
    <>
      {isLoading ? (
        <div className="flex flex-1 items-center justify-center text-sm text-neutral-500">
          Loading conversation…
        </div>
      ) : loadError ? (
        <div className="flex flex-1 items-center justify-center text-sm text-red-400">
          {loadError}
        </div>
      ) : showEmpty ? (
        <EmptyState prompts={SUGGESTED_PROMPTS} onSelectPrompt={handleSend} />
      ) : (
        <ChatThread messages={messages} streamingMessageId={streamingId} />
      )}
      <ChatInput
        onSend={handleSend}
        onStop={handleStop}
        isGenerating={isGenerating}
      />
    </>
  );
}
