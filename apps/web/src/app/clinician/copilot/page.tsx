"use client";

import { Bot } from "lucide-react";
import { Chat } from "@/components/Chat";

export default function Copilot() {
  return (
    <div className="mx-auto flex h-[calc(100vh-11rem)] max-w-4xl flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm md:h-[calc(100vh-8rem)]">
      <div className="flex items-center gap-2 border-b border-stone-200 px-4 py-3">
        <Bot size={18} className="text-teal-700" />
        <div>
          <h1 className="text-sm font-semibold text-stone-900">Clinician Copilot</h1>
          <p className="text-xs text-stone-500">Panel-wide questions. Uses governed MCP tools and clinic protocols; drafts only.</p>
        </div>
      </div>
      <Chat
        endpoint="/clinician/chat"
        emptyTitle="Ask about your panel"
        placeholder="e.g. Which patients have rising FIB-4?"
        suggestions={["Which patients need attention today and why?", "Which patients have FIB-4 above 2.67?", "What does our protocol say about ALT doubling from baseline?"]}
      />
    </div>
  );
}
