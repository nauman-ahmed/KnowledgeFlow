"use client";

import { MOCK_CONVERSATIONS } from "@/lib/mock-data";
import { MobileDrawer } from "./MobileDrawer";
import { Sidebar } from "./Sidebar";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-dvh overflow-hidden">
      <aside className="hidden shrink-0 md:block">
        <Sidebar conversations={MOCK_CONVERSATIONS} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-neutral-800 px-3 py-2 md:hidden">
          <MobileDrawer conversations={MOCK_CONVERSATIONS} />
          <span className="text-sm font-medium text-neutral-200">KnowledgeFlow</span>
        </header>
        {children}
      </div>
    </div>
  );
}
