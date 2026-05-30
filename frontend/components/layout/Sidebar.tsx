"use client";

import { UserButton } from "@clerk/nextjs";
import { MessageSquarePlus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { groupConversationsByDate, type ConversationPreview } from "@/lib/types/chat";
import { cn } from "@/lib/utils";
import { SearchPanel } from "./SearchPanel";

type SidebarProps = {
  conversations: ConversationPreview[];
  onNavigate?: () => void;
  onRefresh?: () => void;
};

export function Sidebar({ conversations, onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const groups = groupConversationsByDate(conversations);

  return (
    <div className="flex h-full w-[260px] flex-col bg-[#212121] text-neutral-200">
      <div className="p-3">
        <Link
          href="/chat"
          onClick={onNavigate}
          className="flex w-full items-center gap-2 rounded-lg border border-neutral-600 px-3 py-2.5 text-sm font-medium transition-colors hover:bg-neutral-800"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New chat
        </Link>
      </div>

      <SearchPanel onNavigate={onNavigate} />

      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {groups.length === 0 ? (
          <p className="px-3 py-2 text-xs text-neutral-500">No conversations yet</p>
        ) : (
          groups.map((group) => (
            <div key={group.label} className="mb-4">
              <p className="px-3 py-2 text-xs font-medium text-neutral-500">{group.label}</p>
              <ul className="space-y-0.5">
                {group.items.map((conv) => {
                  const href = `/chat/${conv.id}`;
                  const active = pathname === href;
                  return (
                    <li key={conv.id}>
                      <Link
                        href={href}
                        onClick={onNavigate}
                        className={cn(
                          "block truncate rounded-lg px-3 py-2 text-sm transition-colors",
                          active
                            ? "bg-neutral-800 text-neutral-100"
                            : "text-neutral-400 hover:bg-neutral-800/60 hover:text-neutral-200",
                        )}
                      >
                        {conv.title}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))
        )}
      </nav>

      <div className="border-t border-neutral-700 p-3">
        <UserButton
          appearance={{
            elements: {
              avatarBox: "h-8 w-8",
            },
          }}
        />
      </div>
    </div>
  );
}
