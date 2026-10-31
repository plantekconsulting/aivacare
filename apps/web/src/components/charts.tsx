"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Point } from "@/lib/types";

// Validated reference palette (categorical slots 1-2) + status colors; text uses ink tokens, never series color.
export const SERIES = ["#2a78d6", "#eb6834"];
export const STATUS = { good: "#0ca30c", warning: "#fab219", critical: "#d03b3b" };
const INK = { primary: "#0b0b0b", secondary: "#52514e", muted: "#8a8984", grid: "#e7e6e2" };

type Series = { key: string; label: string; points: Point[]; unit?: string };
type Band = { from: number; to: number; label: string; tone: keyof typeof STATUS };

const fmtDate = (d: string) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
const fmtDateLong = (d: string) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

export function TrendChart({
  series,
  height = 220,
  bands,
  goal,
  domain,
  decimals = 0,
}: {
  series: Series[];
  height?: number;
  bands?: Band[];
  goal?: { value: number; label: string };
  domain?: [number | "auto", number | "auto"];
  decimals?: number;
}) {
  const byDate = new Map<string, Record<string, number | string>>();
  for (const s of series)
    for (const p of s.points) {
      const k = p.date.slice(0, 10);
      byDate.set(k, { ...(byDate.get(k) ?? { date: k }), [s.key]: Number(p.value.toFixed(decimals)) });
    }
  const rows = [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const unit = series[0]?.unit ?? "";
  if (!rows.length) return <div className="grid h-40 place-items-center text-sm text-stone-500">No data yet</div>;

  return (
    <div style={{ height }} role="img" aria-label={`${series.map((s) => s.label).join(" and ")} trend chart`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
          <CartesianGrid stroke={INK.grid} vertical={false} />
          {bands?.map((b) => (
            <ReferenceArea
              key={b.label}
              y1={b.from}
              y2={b.to}
              fill={STATUS[b.tone]}
              fillOpacity={0.08}
              ifOverflow="hidden"
              label={{ value: b.label, position: "insideTopRight", fill: INK.secondary, fontSize: 10 }}
            />
          ))}
          {goal && (
            <ReferenceLine
              y={goal.value}
              stroke={INK.muted}
              strokeDasharray="4 4"
              label={{ value: goal.label, position: "insideBottomRight", fill: INK.secondary, fontSize: 10 }}
            />
          )}
          <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: INK.muted, fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={28} />
          <YAxis tick={{ fill: INK.muted, fontSize: 11 }} tickLine={false} axisLine={false} domain={domain ?? ["auto", "auto"]} width={48} />
          <Tooltip
            labelFormatter={(d) => fmtDateLong(String(d))}
            formatter={(v, name) => [`${v} ${unit}`.trim(), series.find((s) => s.key === name)?.label ?? name]}
            contentStyle={{ borderRadius: 8, borderColor: INK.grid, fontSize: 12, color: INK.primary }}
          />
          {series.length > 1 && <Legend formatter={(v) => <span style={{ color: INK.secondary, fontSize: 12 }}>{series.find((s) => s.key === v)?.label}</span>} />}
          {series.map((s, i) => (
            <Line
              key={s.key}
              dataKey={s.key}
              type="monotone"
              stroke={SERIES[i]}
              strokeWidth={2}
              dot={rows.length <= 12 ? { r: 4, strokeWidth: 2, stroke: "#fcfcfb", fill: SERIES[i] } : false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: "#fcfcfb" }}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StatTile({
  label,
  point,
  unit,
  decimals = 0,
  status,
  hint,
}: {
  label: string;
  point: Point | null | undefined;
  unit: string;
  decimals?: number;
  status?: { tone: keyof typeof STATUS; text: string };
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-stone-500">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-2xl font-semibold text-stone-900 tabular-nums">{point ? point.value.toFixed(decimals) : "-"}</span>
        <span className="text-sm text-stone-500">{unit}</span>
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs text-stone-500">
        {status && (
          <span className="inline-flex items-center gap-1 font-medium text-stone-700">
            <span className="h-2 w-2 rounded-full" style={{ background: STATUS[status.tone] }} aria-hidden />
            {status.text}
          </span>
        )}
        {point && <span>{fmtDateLong(point.date)}</span>}
      </div>
      {hint && <div className="mt-1 text-xs text-stone-500">{hint}</div>}
    </div>
  );
}

export function fib4Status(v: number | undefined): { tone: keyof typeof STATUS; text: string } | undefined {
  if (v === undefined) return undefined;
  if (v > 2.67) return { tone: "critical", text: "High risk" };
  if (v >= 1.3) return { tone: "warning", text: "Indeterminate" };
  return { tone: "good", text: "Low risk" };
}

export const FIB4_BANDS: Band[] = [
  { from: 0, to: 1.3, label: "Low <1.3", tone: "good" },
  { from: 1.3, to: 2.67, label: "Indeterminate", tone: "warning" },
  { from: 2.67, to: 6, label: "High >2.67", tone: "critical" },
];
