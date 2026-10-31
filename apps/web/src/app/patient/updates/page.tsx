"use client";

import { Bell, CalendarClock, HeartHandshake, Info } from "lucide-react";
import { useEffect } from "react";
import { api, useLive } from "@/lib/api";
import type { Notification } from "@/lib/types";

const ICON = { followup: HeartHandshake, reminder: CalendarClock, info: Info, alert: Bell } as const;

export default function Updates() {
  const { data } = useLive<Notification[]>("/patient/notifications", (e) => e.event === "notification");
  useEffect(() => {
    if (data?.some((n) => !n.read)) {
      const t = setTimeout(() => api("/patient/notifications/read", { method: "POST" }), 4000);
      return () => clearTimeout(t);
    }
  }, [data]);

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold text-stone-900">Updates</h1>
      {!data && <p className="text-sm text-stone-500">Loading…</p>}
      {data?.length === 0 && <p className="text-sm text-stone-500">No updates yet.</p>}
      {data?.map((n) => {
        const Icon = ICON[n.kind as keyof typeof ICON] ?? Info;
        return (
          <div key={n.id} className={`flex gap-3 rounded-2xl border p-4 ${n.read ? "border-stone-200 bg-white" : "border-teal-300 bg-teal-50"}`}>
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white text-teal-700 ring-1 ring-stone-200">
              <Icon size={18} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-stone-900">{n.title}</span>
                {!n.read && <span className="rounded-full bg-teal-700 px-2 text-[10px] font-semibold uppercase text-white">New</span>}
              </div>
              <p className="mt-1 whitespace-pre-line text-sm text-stone-700">{n.body}</p>
              <p className="mt-1 text-xs text-stone-500">{new Date(n.created_at).toLocaleString()}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
