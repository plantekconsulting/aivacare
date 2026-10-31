"use client";

import { ArrowLeft, Bot, CheckCircle2, ClipboardList, FileText } from "lucide-react";
import Link from "next/link";
import { use, useMemo } from "react";
import { AlertReview } from "@/components/AlertReview";
import { Chat } from "@/components/Chat";
import { fib4Bands, StatTile, TrendChart, fib4Status } from "@/components/charts";
import { Card } from "@/components/ui";
import { useLive } from "@/lib/api";
import type { Patient360 } from "@/lib/types";

export default function PatientView({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error, reload } = useLive<Patient360>(`/clinician/patients/${id}`, (e) =>
    (e.event.startsWith("alert") && (e.data as { patient_id?: string }).patient_id === id) || (e.event === "data.updated" && e.data.patient_id === id),
  );
  const context = useMemo(() => ({ patient_id: id }), [id]);

  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!data) return <p className="text-sm text-stone-500">Loading Patient 360…</p>;
  const { profile: p, latest, series, care_plan } = data;

  return (
    <div className="space-y-5">
      <Link href="/clinician" className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-800">
        <ArrowLeft size={14} /> Alert queue
      </Link>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-stone-900">{p.name}</h1>
          <p className="text-sm text-stone-600">
            {p.age}y {p.gender} · MRN {p.mrn} · {p.conditions.join(" · ")}
          </p>
        </div>
        <div className="text-xs text-stone-500">Medications: {p.medications.join("; ")}</div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_400px]">
        <div className="min-w-0 space-y-5">
          {data.open_alerts.map((a) => (
            <AlertReview key={a.id} alert={a} onDone={() => reload()} />
          ))}
          {data.closed_alerts?.slice(0, 2).map((a) => (
            <div key={a.id} className="flex items-start gap-2 rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm">
              <CheckCircle2 size={16} className={a.decision?.approved ? "mt-0.5 text-green-700" : "mt-0.5 text-stone-400"} />
              <div>
                <b>{a.decision?.approved ? "Approved" : "Dismissed"}</b> by {a.decision?.clinician}: {a.title}
                {a.decision?.approved && <div className="text-xs text-stone-600">Actions: {a.decision.actions.join("; ")}</div>}
              </div>
            </div>
          ))}

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="FIB-4" point={latest.FIB4} unit="" decimals={2} status={fib4Status(latest.FIB4?.value)} />
            <StatTile label="ALT" point={latest.ALT} unit="U/L" />
            <StatTile label="Platelets" point={latest.PLT} unit="10³/µL" />
            <StatTile label="HbA1c" point={latest.HBA1C} unit="%" decimals={1} />
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Liver enzymes (U/L)">
              <TrendChart series={[{ key: "ALT", label: "ALT", points: series.ALT, unit: "U/L" }, { key: "AST", label: "AST", points: series.AST, unit: "U/L" }]} goal={{ value: 40, label: "ULN 40" }} />
            </Card>
            <Card title="FIB-4">
              <TrendChart series={[{ key: "FIB4", label: "FIB-4", points: series.FIB4 }]} bands={fib4Bands(5)} domain={[0, 5]} decimals={2} />
            </Card>
            <Card title="Weight (kg) - Apple Watch / scale">
              <TrendChart series={[{ key: "WEIGHT", label: "Weight", points: series.WEIGHT.slice(-120), unit: "kg" }]} decimals={1} />
            </Card>
            <Card title="Daily steps - Apple Watch">
              <TrendChart series={[{ key: "STEPS", label: "Steps", points: series.STEPS.slice(-120), unit: "steps" }]} goal={{ value: 8000, label: "Goal" }} />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card title={<span className="flex items-center gap-2"><ClipboardList size={16} className="text-teal-700" /> Care plan</span>} action={<span className="text-xs text-stone-500">{care_plan.version}</span>}>
              <ul className="space-y-1.5 text-sm text-stone-700">
                {care_plan.activities.map((a) => <li key={a}>• {a}</li>)}
              </ul>
            </Card>
            <Card title={<span className="flex items-center gap-2"><FileText size={16} className="text-teal-700" /> Patient-uploaded documents</span>}>
              {!data.documents?.length && <p className="text-sm text-stone-500">None</p>}
              <ul className="space-y-1.5 text-sm">
                {data.documents?.map((d) => (
                  <li key={d.id} className="flex justify-between gap-2"><span>{d.filename}</span><span className="text-xs text-stone-500">{d.status}</span></li>
                ))}
              </ul>
            </Card>
          </div>
        </div>

        <div className="xl:sticky xl:top-20 xl:h-[calc(100vh-7rem)]">
          <div className="flex h-[560px] flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm xl:h-full">
            <div className="flex items-center gap-2 border-b border-stone-200 px-4 py-3 text-sm font-semibold text-stone-900">
              <Bot size={16} className="text-teal-700" /> Clinician Copilot
            </div>
            <Chat
              compact
              endpoint="/clinician/chat"
              context={context}
              emptyTitle={`Ask about ${p.name.split(" ")[0]}'s record`}
              placeholder="Ask the Copilot…"
              suggestions={["What changed in the last 90 days?", "Is this patient a candidate for resmetirom per protocol?", "Summarize wearable trends since the last visit"]}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
