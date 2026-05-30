import { ChatView } from "@/components/chat/ChatView";

type PageProps = {
  params: Promise<{ conversationId: string }>;
};

export default async function ConversationPage({ params }: PageProps) {
  const { conversationId } = await params;

  return (
    <main className="flex min-h-0 flex-1 flex-col">
      <ChatView conversationId={conversationId} />
    </main>
  );
}
