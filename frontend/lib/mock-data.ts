export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
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

const now = new Date();
const today = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 14, 30);
const yesterday = new Date(today);
yesterday.setDate(yesterday.getDate() - 1);
const lastWeek = new Date(today);
lastWeek.setDate(lastWeek.getDate() - 5);

export const MOCK_CONVERSATIONS: ConversationPreview[] = [
  { id: "conv-1", title: "Topics in the library", updatedAt: today },
  { id: "conv-2", title: "Compound interest basics", updatedAt: yesterday },
  { id: "conv-3", title: "Study habits summary", updatedAt: lastWeek },
];

export const MOCK_MESSAGES: Record<string, ChatMessage[]> = {
  "conv-1": [
    {
      id: "m1",
      role: "user",
      content: "What topics are covered in the knowledge library?",
    },
    {
      id: "m2",
      role: "assistant",
      content:
        "The curated library includes introductory material on **investing**, **music theory**, **study habits**, and **compound interest**. Each document is a self-contained guide you can ask about in chat once ingestion is enabled in a later milestone.",
    },
  ],
  "conv-2": [
    {
      id: "m3",
      role: "user",
      content: "Explain compound interest in simple terms.",
    },
    {
      id: "m4",
      role: "assistant",
      content:
        "Compound interest means you earn interest on both your original amount **and** on interest you have already earned. Over time, growth accelerates because each period builds on a larger balance.",
    },
  ],
  "conv-3": [
    {
      id: "m5",
      role: "user",
      content: "What are good study habits?",
    },
    {
      id: "m6",
      role: "assistant",
      content:
        "Effective habits include **spaced repetition**, active recall, focused sessions with breaks, and reviewing material on a schedule rather than cramming.",
    },
  ],
};

export const MOCK_ASSISTANT_REPLY =
  "This is a mock reply for Milestone M1. Real answers from your knowledge library will arrive in M3 when RAG chat is wired up.";

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
