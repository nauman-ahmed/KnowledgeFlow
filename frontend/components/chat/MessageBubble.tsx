import type { ChatMessage } from "@/lib/types/chat";
import { AssistantMessage } from "./AssistantMessage";
import { UserMessage } from "./UserMessage";

type MessageBubbleProps = {
  message: ChatMessage;
  isStreaming?: boolean;
};

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  if (message.role === "user") {
    return <UserMessage content={message.content} />;
  }
  return (
    <AssistantMessage
      content={message.content}
      isStreaming={isStreaming}
      sources={message.sources}
      structured={message.structured}
      graphContext={message.graphContext}
    />
  );
}
