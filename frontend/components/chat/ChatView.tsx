"use client";

import { useCallback, useRef, useState } from "react";
import {
  MOCK_ASSISTANT_REPLY,
  SUGGESTED_PROMPTS,
  type ChatMessage,
} from "@/lib/mock-data";
import { ChatInput } from "./ChatInput";
import { ChatThread } from "./ChatThread";
import { EmptyState } from "./EmptyState";

type ChatViewProps = {
  initialMessages?: ChatMessage[];
};

function createId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatView({ initialMessages = [] }: ChatViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const streamIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearStreamInterval = useCallback(() => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
  }, []);

  const appendExchange = useCallback((userText: string) => {
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

    // Mock streaming: reveal assistant text in chunks
    const full = MOCK_ASSISTANT_REPLY;
    let index = 0;
    const chunkSize = 8;
    clearStreamInterval();
    streamIntervalRef.current = setInterval(() => {
      index = Math.min(index + chunkSize, full.length);
      const slice = full.slice(0, index);
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, content: slice } : m)),
      );
      if (index >= full.length) {
        clearStreamInterval();
        setIsGenerating(false);
        setStreamingId(null);
      }
    }, 40);
  }, [clearStreamInterval]);

  const handleSend = useCallback(
    (text: string) => {
      if (isGenerating) return;
      appendExchange(text);
    },
    [appendExchange, isGenerating],
  );

  const handleStop = useCallback(() => {
    clearStreamInterval();
    setIsGenerating(false);
    setStreamingId(null);
  }, [clearStreamInterval]);

  const showEmpty = messages.length === 0;

  return (
    <>
      {showEmpty ? (
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
