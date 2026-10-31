import { Text, View } from "react-native";
import Svg, { Circle, Line, Polyline, Rect } from "react-native-svg";

type Pt = { date: string; value: number };
const SERIES = "#2a78d6";
const GRID = "#e7e6e2";

/** Minimal single-series trend line with optional goal line and shaded bands (validated palette). */
export function LineChart({
  points,
  height = 120,
  goal,
  bands,
  domain,
}: {
  points: Pt[];
  height?: number;
  goal?: number;
  bands?: { from: number; to: number; color: string }[];
  domain?: [number, number];
}) {
  const width = 320;
  const pad = 8;
  if (points.length < 2) return <Text style={{ color: "#8a8984", fontSize: 12 }}>Not enough data yet</Text>;
  const vals = points.map((p) => p.value).concat(goal !== undefined ? [goal] : []);
  const lo = domain?.[0] ?? Math.min(...vals) * 0.95;
  const hi = domain?.[1] ?? Math.max(...vals) * 1.05;
  const x = (i: number) => pad + (i / (points.length - 1)) * (width - pad * 2);
  const y = (v: number) => pad + (1 - (v - lo) / (hi - lo || 1)) * (height - pad * 2);
  const last = points[points.length - 1];
  return (
    <View>
      <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        {bands?.map((b) => (
          <Rect key={b.from} x={pad} width={width - pad * 2} y={y(Math.min(b.to, hi))} height={Math.max(0, y(Math.max(b.from, lo)) - y(Math.min(b.to, hi)))} fill={b.color} opacity={0.1} />
        ))}
        {[0.25, 0.5, 0.75].map((f) => (
          <Line key={f} x1={pad} x2={width - pad} y1={pad + f * (height - pad * 2)} y2={pad + f * (height - pad * 2)} stroke={GRID} strokeWidth={1} />
        ))}
        {goal !== undefined && <Line x1={pad} x2={width - pad} y1={y(goal)} y2={y(goal)} stroke="#8a8984" strokeDasharray="4 4" strokeWidth={1} />}
        <Polyline points={points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ")} fill="none" stroke={SERIES} strokeWidth={2} strokeLinejoin="round" />
        <Circle cx={x(points.length - 1)} cy={y(last.value)} r={4} fill={SERIES} stroke="#fcfcfb" strokeWidth={2} />
      </Svg>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text style={{ fontSize: 10, color: "#8a8984" }}>{points[0].date.slice(0, 10)}</Text>
        <Text style={{ fontSize: 10, color: "#8a8984" }}>{last.date.slice(0, 10)}</Text>
      </View>
    </View>
  );
}
