"use client";

import { BookOpen, Bot, CheckCircle2, Hourglass, Loader2, Plus, Sparkles, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { api, getSession } from "@/lib/api";
import type { Alert, Review } from "@/lib/types";
import { Button, PriorityBadge, slaText } from "./ui";

export function AlertReview({ alert, onDone }: { alert: Alert; onDone: () => void }) {
  const review: Review | null = alert.ai_summary ? JSON.parse(alert.ai_summary) : null;
  const proposed = alert.proposal?.actions ?? [];
  const [actions, setActions] = useState<{ text: string; on: boolean }[]>([]);
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  // Physicians approve; coordinators triage. Sessions from before this flag existed default to the old behaviour (the server enforces it either way).
  const [approver, setApprover] = useState(true);
  useEffect(() => {
    setApprover(getSession()?.can_approve ?? true);
  }, []);

  useEffect(() => setActions(proposed.map((t) => ({ text: t, on: true }))), [alert.proposal?.actions?.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps

  const act = async (kind: "ack" | "approve" | "dismiss") => {
    setBusy(kind);
    setErr(null);
    try {
      if (kind === "ack") await api(`/clinician/alerts/${alert.id}/acknowledge`, { method: "POST" });
      else
        await api(`/clinician/alerts/${alert.id}/decision`, {
          method: "POST",
          body: JSON.stringify({ approved: kind === "approve", actions: actions.filter((a) => a.on).map((a) => a.text) }),
        });
      onDone();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="rounded-2xl border-2 border-red-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <PriorityBadge p={alert.priority} />
          <span className="font-semibold text-stone-900">{alert.title}</span>
        </div>
        <span className="text-xs text-stone-500">
          {alert.status} · {slaText(alert.sla_due)} · source: {alert.source}
        </span>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {alert.hits.map((h) => (
          <div key={h.rule_id} className="rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-700">
            <div className="font-medium text-stone-900">Rule: {h.rule_id}</div>
            {h.metric !== "SYMPTOM" ? <div>Value {h.value} (threshold {JSON.stringify((h as unknown as { threshold: unknown }).threshold)})</div> : <div>“{String(h.evidence.reported ?? "")}”</div>}
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl bg-teal-50/60 p-4">
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-teal-800">
          <Sparkles size={14} /> Copilot review {review && <span className="font-normal normal-case text-teal-700">· {review.generated_by}</span>}
        </div>
        {!review ? (
          <div className="flex items-center gap-2 text-sm text-stone-500">
            <Loader2 size={14} className="animate-spin" /> Preparing summary from the record and protocols…
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-stone-900">{review.headline}</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-stone-700">
              {review.summary_bullets.map((b) => <li key={b}>{b}</li>)}
            </ul>
            <p className="mt-2 text-xs text-stone-600">{review.rationale}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {review.sources.map((s) => (
                <span key={s.id} className="inline-flex items-center gap-1 rounded-md border border-teal-200 bg-white px-2 py-0.5 text-[11px] text-stone-700">
                  <BookOpen size={11} className="text-teal-700" /> <b>{s.id}</b> {s.title} - {s.section}
                </span>
              ))}
            </div>
          </>
        )}
      </div>

      {alert.status !== "completed" && alert.status !== "cancelled" && (
        <div className="mt-4">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-stone-600">
            <Bot size={14} /> Proposed care-plan actions - {approver ? "draft, edit before approving" : "draft for physician review"}
          </div>
          <div className="space-y-1.5">
            {actions.map((a, i) => (
              <label key={i} className="flex cursor-pointer items-start gap-2 rounded-lg border border-stone-200 px-3 py-2 text-sm hover:bg-stone-50">
                <input type="checkbox" checked={a.on} disabled={!approver} onChange={() => setActions(actions.map((x, j) => (j === i ? { ...x, on: !x.on } : x)))} className="mt-0.5 accent-teal-700" />
                <span className="text-stone-800">{a.text}</span>
              </label>
            ))}
            {approver && <div className="flex gap-2">
              <input
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
                placeholder="Add an action…"
                className="flex-1 rounded-lg border border-stone-300 px-3 py-1.5 text-sm outline-none focus:border-teal-600"
              />
              <Button
                variant="secondary"
                onClick={() => {
                  if (custom.trim()) setActions([...actions, { text: custom.trim(), on: true }]);
                  setCustom("");
                }}
              >
                <Plus size={14} /> Add
              </Button>
            </div>}
          </div>
          {err && <p className="mt-2 text-sm text-red-700">{err}</p>}
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            {alert.status === "requested" && (
              <Button variant="ghost" onClick={() => act("ack")} disabled={!!busy}>
                Acknowledge
              </Button>
            )}
            {approver ? (
              <>
                <Button variant="secondary" onClick={() => act("dismiss")} disabled={!!busy}>
                  <XCircle size={16} /> Dismiss
                </Button>
                <Button onClick={() => act("approve")} disabled={!!busy || !actions.some((a) => a.on)}>
                  {busy === "approve" ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />} Approve &amp; notify patient
                </Button>
              </>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <Hourglass size={15} /> Awaiting physician approval
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
