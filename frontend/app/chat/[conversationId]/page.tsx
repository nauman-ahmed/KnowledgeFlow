import { ChatView } from "@/components/chat/ChatView";
import { MOCK_MESSAGES } from "@/lib/mock-data";
import { notFound } from "next/navigation";

type PageProps = {
  params: Promise<{ conversationId: string }>;
};

export default async function ConversationPage({ params }: PageProps) {
  const { conversationId } = await params;
  const initialMessages = MOCK_MESSAGES[conversationId];

  if (!initialMessages) {
    notFound();
  }

  return (
    <main className="flex min-h-0 flex-1 flex-col">
      <ChatView initialMessages={initialMessages} />
    </main>
  );
}
