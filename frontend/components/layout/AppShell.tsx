"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchConversations } from "@/lib/api/conversations";
import { useApiAuth } from "@/lib/api/use-api-auth";
import type { ConversationPreview } from "@/lib/types/chat";
import { MobileDrawer } from "./MobileDrawer";
import { Sidebar } from "./Sidebar";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const { isAuthReady, getApiToken } = useApiAuth();
  const [conversations, setConversations] = useState<ConversationPreview[]>([]);

  const loadConversations = useCallback(async () => {
    if (!isAuthReady) return;
    try {
      const token = await getApiToken();
      if (!token) return;
      const list = await fetchConversations(token);
      setConversations(list);
    } catch {
      setConversations([]);
    }
  }, [getApiToken, isAuthReady]);

  useEffect(() => {
    if (!isAuthReady) return;

    let cancelled = false;

    async function load() {
      try {
        const token = await getApiToken();
        if (!token || cancelled) return;
        const list = await fetchConversations(token);
        if (!cancelled) setConversations(list);
      } catch {
        if (!cancelled) setConversations([]);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [getApiToken, isAuthReady]);

  useEffect(() => {
    if (!isAuthReady) return;
    const onFocus = () => {
      void loadConversations();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [isAuthReady, loadConversations]);

  return (
    <div className="flex h-dvh overflow-hidden">
      <aside className="hidden shrink-0 md:block">
        <Sidebar conversations={conversations} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-neutral-800 px-3 py-2 md:hidden">
          <MobileDrawer conversations={conversations} />
          <span className="text-sm font-medium text-neutral-200">KnowledgeFlow</span>
        </header>
        {children}
      </div>
    </div>
  );
}
