"use client";

import clsx from "clsx";
import { Bot, ChevronRight, Clock, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Card, PriorityBadge, slaText } from "@/components/ui";
import { onLiveEvent, useLive } from "@/lib/api";
import type { Alert } from "@/lib/types";

export default function AlertQueue() {
  const { data } = useLive<Alert[]>("/clinician/alerts", (e) => e.event.startsWith("alert") || e.event === "poll");
  const [toast, setToast] = useState<Alert | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(
    () =>
      onLiveEvent((e) => {
        if (e.event === "alert.created") {
          const a = e.data as unknown as Alert;
          setToast(a);
          setFlash(a.id);
          clearTimeout(timer.current);
          timer.current = setTimeout(() => setToast(null), 8000);
        }
      }),
    [],
  );

  const open = data ?? [];
  const counts = { high: open.filter((a) => a.priority === "high").length, medium: open.filter((a) => a.priority === "medium").length, low: open.filter((a) => a.priority === "low").length };

  return (
    <div className="space-y-5">
      {toast && (
        <Link href={`/clinician/patients/${toast.patient_id}`} className="fixed right-6 top-20 z-30 flex max-w-sm animate-[pulse_1s_ease-in-out_2] items-start gap-3 rounded-2xl border border-red-200 bg-white p-4 shadow-xl">
          <PriorityBadge p={toast.priority} />
          <div>
            <div className="text-sm font-semibold text-stone-900">New alert: {toast.patient_name}</div>
            <div className="text-xs text-stone-600">{toast.title}</div>
          </div>
        </Link>
      )}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-stone-900">Alert queue</h1>
          <p className="text-sm text-stone-600">Raised by deterministic clinical rules. AI prepares the review; you decide.</p>
        </div>
        <div className="flex gap-2 text-sm">
          {(["high", "medium", "low"] as const).map((p) => (
            <span key={p} className="flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-1.5">
              <PriorityBadge p={p} /> <b className="tabular-nums">{counts[p]}</b>
            </span>
          ))}
        </div>
      </div>

      <Card>
        {!data && <p className="text-sm text-stone-500">Loading…</p>}
        {data?.length === 0 && <p className="py-6 text-center text-sm text-stone-500">No open alerts. 🎉</p>}
        <ul className="divide-y divide-stone-100">
          {open.map((a) => (
            <li key={a.id}>
              <Link
                href={`/clinician/patients/${a.patient_id}`}
                className={clsx("flex items-center gap-4 rounded-xl px-2 py-3 transition hover:bg-stone-50", flash === a.id && "bg-red-50/60")}
              >
                <PriorityBadge p={a.priority} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-stone-900">{a.patient_name}</span>
                    {a.status !== "requested" && <span className="rounded bg-stone-100 px-1.5 text-[11px] text-stone-600">{a.status}</span>}
                    {a.source !== "rules-engine" && <span className="rounded bg-violet-50 px-1.5 text-[11px] text-violet-800">{a.source}</span>}
                  </div>
                  <div className="truncate text-sm text-stone-600">{a.title}</div>
                </div>
                <div className="hidden items-center gap-1 text-xs sm:flex">
                  {a.ai_summary ? (
                    <span className="flex items-center gap-1 text-teal-800"><Sparkles size={13} /> AI review ready</span>
                  ) : (
                    <span className="flex items-center gap-1 text-stone-400"><Bot size={13} className="animate-pulse" /> AI reviewing…</span>
                  )}
                </div>
                <div className={clsx("flex w-28 items-center justify-end gap-1 text-xs", a.sla_due && new Date(a.sla_due) < new Date() ? "font-medium text-red-700" : "text-stone-500")}>
                  <Clock size={13} /> {slaText(a.sla_due)}
                </div>
                <ChevronRight size={16} className="text-stone-400" />
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
