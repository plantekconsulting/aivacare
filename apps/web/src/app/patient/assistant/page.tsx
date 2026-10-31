"use client";

import { ShieldCheck } from "lucide-react";
import { Chat } from "@/components/Chat";

export default function Assistant() {
  return (
    <div className="flex h-[calc(100vh-11rem)] flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm md:h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between border-b border-stone-200 px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold text-stone-900">AivaCare Assistant</h1>
          <p className="text-xs text-stone-500">Answers use your records and LiverWell-approved guidance, with sources.</p>
        </div>
        <span className="hidden items-center gap-1 text-xs text-stone-500 sm:flex">
          <ShieldCheck size={14} className="text-teal-700" /> Not for emergencies - call 911
        </span>
      </div>
      <Chat
        endpoint="/patient/chat"
        emptyTitle="Ask me about your results, trends or care plan"
        placeholder="Ask a question…"
        suggestions={[
          "Why is my ALT high and what should I eat?",
          "How am I doing against my weight goal?",
          "What does my FIB-4 score mean?",
          "My eyes look yellow today",
        ]}
      />
    </div>
  );
}
