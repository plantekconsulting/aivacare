"use client";

import Link from "next/link";
import { fib4Status, STATUS } from "@/components/charts";
import { Card, PriorityBadge } from "@/components/ui";
import { useLive } from "@/lib/api";

type Row = { patient_id: string; name: string; open_alerts: number; top_priority: "high" | "medium" | "low" | null; fib4: number | null; fib4_prev: number | null; alt: number | null; last_lab: string | null };

export default function Panel() {
  const { data } = useLive<Row[]>("/clinician/panel", (e) => e.event.startsWith("alert") || e.event === "data.updated");
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Patient panel</h1>
        <p className="text-sm text-stone-600">Risk-ranked by open alerts and latest FIB-4.</p>
      </div>
      <Card>
        {!data && <p className="text-sm text-stone-500">Loading…</p>}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-xs uppercase text-stone-500">
                <th className="py-2">Patient</th><th>Open alerts</th><th>FIB-4 (prev → latest)</th><th>ALT U/L</th><th>Last lab</th>
              </tr>
            </thead>
            <tbody>
              {data?.map((r) => {
                const st = fib4Status(r.fib4 ?? undefined);
                return (
                  <tr key={r.patient_id} className="border-b border-stone-100 hover:bg-stone-50">
                    <td className="py-2.5"><Link href={`/clinician/patients/${r.patient_id}`} className="font-medium text-teal-800 hover:underline">{r.name}</Link></td>
                    <td>{r.top_priority ? <span className="flex items-center gap-2"><PriorityBadge p={r.top_priority} /> {r.open_alerts}</span> : <span className="text-stone-400">-</span>}</td>
                    <td className="tabular-nums">
                      <span className="text-stone-500">{r.fib4_prev?.toFixed(2) ?? "-"}</span> → <b>{r.fib4?.toFixed(2) ?? "-"}</b>
                      {st && <span className="ml-2 inline-flex items-center gap-1 text-xs text-stone-600"><span className="h-2 w-2 rounded-full" style={{ background: STATUS[st.tone] }} />{st.text}</span>}
                    </td>
                    <td className="tabular-nums">{r.alt ?? "-"}</td>
                    <td className="text-stone-500">{r.last_lab}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
