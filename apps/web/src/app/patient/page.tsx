"use client";

import { ClipboardList, MessageCircleHeart } from "lucide-react";
import Link from "next/link";
import { fib4Bands, StatTile, TrendChart, fib4Status } from "@/components/charts";
import { Card } from "@/components/ui";
import { useLive } from "@/lib/api";
import type { Patient360 } from "@/lib/types";

export default function PatientHome() {
  const { data, error } = useLive<Patient360>("/patient/home", (e) => ["data.updated", "notification"].includes(e.event));
  if (error) return <p className="text-sm text-red-700">{error}</p>;
  if (!data) return <p className="text-sm text-stone-500">Loading your health summary…</p>;

  const { profile, latest, series, care_plan } = data;
  const first = profile.name.split(" ")[0];
  const w = series.WEIGHT;
  const steps7 = series.STEPS.slice(-7);
  const avgSteps = steps7.length ? Math.round(steps7.reduce((a, p) => a + p.value, 0) / steps7.length) : 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-stone-900">Hi {first}</h1>
          <p className="text-sm text-stone-600">Your liver health at a glance - labs from LiverWell, daily data from your Apple Watch.</p>
        </div>
        <Link href="/patient/assistant" className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800">
          <MessageCircleHeart size={16} /> Ask about my results
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="ALT (liver enzyme)" point={latest.ALT} unit="U/L" status={latest.ALT && latest.ALT.value > 40 ? { tone: "warning", text: "Above normal" } : { tone: "good", text: "Normal" }} />
        <StatTile label="FIB-4 score" point={latest.FIB4} unit="" decimals={2} status={fib4Status(latest.FIB4?.value)} />
        <StatTile label="Weight" point={latest.WEIGHT} unit="kg" decimals={1} hint={w.length ? `Started at ${w[0].value.toFixed(1)} kg` : undefined} />
        <StatTile label="Steps (7-day avg)" point={latest.STEPS ? { ...latest.STEPS, value: avgSteps } : null} unit="/day" hint="Goal 8,000 / day" />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Liver enzymes (U/L)">
          <TrendChart series={[{ key: "ALT", label: "ALT", points: series.ALT, unit: "U/L" }, { key: "AST", label: "AST", points: series.AST, unit: "U/L" }]} goal={{ value: 40, label: "ALT upper normal 40" }} />
        </Card>
        <Card title="FIB-4 fibrosis risk score">
          <TrendChart series={[{ key: "FIB4", label: "FIB-4", points: series.FIB4 }]} bands={fib4Bands(4)} domain={[0, 4]} decimals={2} />
        </Card>
        <Card title="Weight (kg) - from your watch & scale">
          <TrendChart series={[{ key: "WEIGHT", label: "Weight", points: series.WEIGHT, unit: "kg" }]} decimals={1} />
        </Card>
        <Card title="Daily steps">
          <TrendChart series={[{ key: "STEPS", label: "Steps", points: series.STEPS, unit: "steps" }]} goal={{ value: 8000, label: "Goal 8,000" }} />
        </Card>
      </div>

      <Card title={<span className="flex items-center gap-2"><ClipboardList size={16} className="text-teal-700" /> My care plan</span>} action={<span className="text-xs text-stone-500">{care_plan.version}</span>}>
        <ul className="space-y-2">
          {care_plan.activities.map((a) => (
            <li key={a} className="flex gap-2 text-sm text-stone-700">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" /> {a}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
