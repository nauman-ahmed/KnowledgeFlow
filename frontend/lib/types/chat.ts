export type SourceCitation = {
  document: string;
  excerpt: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
};

export type ConversationPreview = {
  id: string;
  title: string;
  updatedAt: Date;
};

export const SUGGESTED_PROMPTS = [
  "What topics are covered in the knowledge library?",
  "Summarize the main ideas from the documents",
  "Explain compound interest in simple terms",
  "What are effective study habits for learning new material?",
] as const;

export function groupConversationsByDate(
  conversations: ConversationPreview[],
): { label: string; items: ConversationPreview[] }[] {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfWeek = new Date(startOfToday);
  startOfWeek.setDate(startOfWeek.getDate() - 7);

  const groups: Record<string, ConversationPreview[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };

  for (const conv of conversations) {
    const t = conv.updatedAt;
    if (t >= startOfToday) groups.Today.push(conv);
    else if (t >= startOfYesterday) groups.Yesterday.push(conv);
    else if (t >= startOfWeek) groups["Previous 7 days"].push(conv);
    else groups.Older.push(conv);
  }

  return (["Today", "Yesterday", "Previous 7 days", "Older"] as const)
    .map((label) => ({ label, items: groups[label] }))
    .filter((g) => g.items.length > 0);
}
