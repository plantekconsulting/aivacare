"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { BookOpen, Check, Loader2, Send, Wrench } from "lucide-react";
import { useMemo, useRef, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { API_URL, getSession } from "@/lib/api";

type Source = { id: string; title: string; section: string; version: string; approved_by: string; excerpt: string };
type ToolStatus = { label: string; status: "running" | "done" | "error" };

/** API errors arrive as FastAPI JSON ({"detail": "..."}); show just the message. */
function errorText(message: string) {
  try {
    return JSON.parse(message).detail ?? message;
  } catch {
    return message || "Something went wrong.";
  }
}

export function Chat({
  endpoint,
  suggestions,
  placeholder,
  context,
  emptyTitle,
  compact,
}: {
  endpoint: string;
  suggestions: string[];
  placeholder: string;
  context?: Record<string, string>;
  emptyTitle: string;
  compact?: boolean;
}) {
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${API_URL}${endpoint}`,
        headers: (): Record<string, string> => ({ Authorization: `Bearer ${getSession()?.token ?? ""}` }),
        body: () => context ?? {},
      }),
    [endpoint, context],
  );
  const { messages, sendMessage, status, error } = useChat({ transport });
  const [input, setInput] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const busy = status === "submitted" || status === "streaming";

  // Block body on purpose: newer browsers return a Promise from scrollIntoView, which React would call as a cleanup.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const send = (text: string) => {
    if (!text.trim() || busy) return;
    sendMessage({ text });
    setInput("");
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className={`flex-1 space-y-4 overflow-y-auto ${compact ? "p-3" : "p-4"}`}>
        {messages.length === 0 && (
          <div className="py-6 text-center">
            <p className="text-sm font-medium text-stone-800">{emptyTitle}</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button key={s} onClick={() => send(s)} className="rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-left text-xs text-teal-900 hover:bg-teal-100">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => {
          const text = m.parts.map((p) => (p.type === "text" ? p.text : "")).join("");
          const tools = m.parts.filter((p) => p.type === "data-tool").map((p) => (p as unknown as { data: ToolStatus }).data);
          const sources = m.parts.filter((p) => p.type === "data-source").map((p) => (p as unknown as { data: Source }).data);
          if (m.role === "user")
            return (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-teal-700 px-4 py-2 text-sm text-white">{text}</div>
              </div>
            );
          return (
            <div key={m.id} className="max-w-[92%] space-y-2">
              {tools.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {tools.map((t, i) => (
                    <span key={i} className="inline-flex items-center gap-1 rounded-md bg-stone-100 px-2 py-0.5 text-[11px] text-stone-600">
                      {t.status === "running" ? <Loader2 size={11} className="animate-spin" /> : t.status === "done" ? <Check size={11} /> : <Wrench size={11} />}
                      {t.label}
                    </span>
                  ))}
                </div>
              )}
              {text && (
                <div className="md rounded-2xl rounded-bl-sm bg-stone-100 px-4 py-3 text-sm text-stone-900">
                  <ReactMarkdown>{text}</ReactMarkdown>
                </div>
              )}
              {sources.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((s) => (
                    <span
                      key={s.id}
                      title={`${s.section}\n\n${s.excerpt}…\n\nApproved by ${s.approved_by}`}
                      className="inline-flex cursor-help items-center gap-1 rounded-md border border-stone-200 bg-white px-2 py-0.5 text-[11px] text-stone-700"
                    >
                      <BookOpen size={11} className="text-teal-700" />
                      <b>{s.id}</b> {s.title} · v{s.version}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {status === "submitted" && (
          <div className="flex items-center gap-2 text-xs text-stone-500">
            <Loader2 size={14} className="animate-spin" /> Thinking…
          </div>
        )}
        {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">{errorText(error.message)}</div>}
        <div ref={bottom} />
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-stone-200 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          maxLength={2000}
          className="flex-1 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
        />
        <button type="submit" disabled={busy || !input.trim()} className="rounded-xl bg-teal-700 px-3 text-white disabled:opacity-40" aria-label="Send">
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
