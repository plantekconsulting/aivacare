"use client";

import { Card, PriorityBadge } from "@/components/ui";
import { useLive } from "@/lib/api";
import type { Priority } from "@/lib/types";

type Rule = { id: string; metric: string; kind: string; threshold: number | number[]; priority: Priority; title: string; suggested_action: string };
type Catalog = { version: string; sla_hours: Record<string, number>; rules: Rule[]; red_flags: { term: string; patterns: string[] }[] };
type Audit = { actor: string; action: string; detail: Record<string, unknown>; created_at: string };

export default function Governance() {
  const { data: cat } = useLive<Catalog>("/clinician/rules");
  const { data: audit } = useLive<Audit[]>("/clinician/audit", () => true);
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Card title={`Clinical rule catalog · ${cat?.version ?? ""}`} action={<span className="text-xs text-stone-500">Deterministic - AI never decides if a rule fires</span>}>
        <ul className="divide-y divide-stone-100">
          {cat?.rules.map((r) => (
            <li key={r.id} className="py-2.5">
              <div className="flex items-center gap-2">
                <PriorityBadge p={r.priority} />
                <span className="text-sm font-medium text-stone-900">{r.title}</span>
              </div>
              <div className="mt-1 text-xs text-stone-600">
                <code>{r.id}</code> · {r.metric} {r.kind.replaceAll("_", " ")} {JSON.stringify(r.threshold)} · SLA {cat.sla_hours[r.priority]}h
              </div>
            </li>
          ))}
        </ul>
        <h3 className="mt-4 text-sm font-semibold text-stone-800">Red-flag symptoms (bypass AI, urgent escalation)</h3>
        <p className="mt-1 text-xs text-stone-600">{cat?.red_flags.map((f) => f.term).join(" · ")}</p>
      </Card>
      <Card title="Audit trail" action={<span className="text-xs text-stone-500">latest 100 events</span>}>
        <ul className="max-h-[70vh] divide-y divide-stone-100 overflow-y-auto text-sm">
          {audit?.map((a, i) => (
            <li key={i} className="py-2">
              <div className="flex justify-between gap-2">
                <span><b className="text-stone-900">{a.action}</b> <span className="text-stone-500">by {a.actor}</span></span>
                <span className="shrink-0 text-xs text-stone-500">{new Date(a.created_at).toLocaleTimeString()}</span>
              </div>
              <div className="truncate text-xs text-stone-500">{JSON.stringify(a.detail)}</div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
