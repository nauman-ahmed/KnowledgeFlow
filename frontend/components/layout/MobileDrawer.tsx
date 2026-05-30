"use client";

import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import type { ConversationPreview } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type MobileDrawerProps = {
  conversations: ConversationPreview[];
};

export function MobileDrawer({ conversations }: MobileDrawerProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-10 w-10 items-center justify-center rounded-lg text-neutral-300 hover:bg-neutral-800 md:hidden"
        aria-label="Open sidebar"
      >
        <Menu className="h-5 w-5" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close sidebar"
            onClick={() => setOpen(false)}
          />
          <div
            className={cn(
              "absolute inset-y-0 left-0 shadow-2xl transition-transform",
              open ? "translate-x-0" : "-translate-x-full",
            )}
          >
            <div className="relative flex h-full">
              <Sidebar conversations={conversations} onNavigate={() => setOpen(false)} />
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="absolute right-2 top-3 flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 hover:bg-neutral-800"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
