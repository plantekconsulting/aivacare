"use client";

import { Activity, FlaskConical, RotateCcw, Watch } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "@/components/Shell";
import { Button, Card, Logo } from "@/components/ui";
import { api, onLiveEvent, type LiveEvent } from "@/lib/api";

type Status = { fhir: boolean; llm_configured: boolean; model_main: string; model_fast: string };

export default function Admin() {
  const session = useSession(["admin"]);
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [log, setLog] = useState<(LiveEvent & { at: string })[]>([]);

  useEffect(() => {
    if (!session) return;
    api<Status>("/admin/status").then(setStatus).catch(() => setStatus(null));
    return onLiveEvent((e) => e.event !== "poll" && setLog((l) => [{ ...e, at: new Date().toLocaleTimeString() }, ...l].slice(0, 40)));
  }, [session]);

  if (!session) return null;

  const run = async (key: string, path: string, body?: object) => {
    setBusy(key);
    setResult(null);
    try {
      const r = await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
      setResult(JSON.stringify(r, null, 2));
    } catch (e) {
      setResult(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="mx-auto max-w-5xl space-y-5 px-4 py-6">
      <div className="flex items-center justify-between">
        <Logo small />
        <a href="/" className="text-sm text-teal-800 hover:underline">Switch persona</a>
      </div>
      <h1 className="text-2xl font-semibold text-stone-900">Presenter controls</h1>

      <div className="flex flex-wrap gap-3 text-sm">
        <span className={`rounded-lg px-3 py-1.5 ${status?.fhir ? "bg-green-50 text-green-900" : "bg-red-50 text-red-900"}`}>FHIR server: {status?.fhir ? "up" : "down"}</span>
        <span className={`rounded-lg px-3 py-1.5 ${status?.llm_configured ? "bg-green-50 text-green-900" : "bg-amber-50 text-amber-900"}`}>
          Claude API: {status?.llm_configured ? `configured (${status.model_main} / ${status.model_fast})` : "NOT configured - AI features use fallbacks"}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card title="1. Reset demo">
          <p className="mb-3 text-sm text-stone-600">Restore synthetic data: John Miller + 8 panel patients, fresh alert queue.</p>
          <Button variant="secondary" onClick={() => run("reset", "/admin/reset")} disabled={!!busy}>
            <RotateCcw size={16} /> {busy === "reset" ? "Resetting…" : "Reset"}
          </Button>
        </Card>
        <Card title="2. Lab feed: new results for John">
          <p className="mb-3 text-sm text-stone-600">ALT 96, AST 88, PLT 150 arrive from the lab → FIB-4 2.87 → high-priority alert.</p>
          <Button onClick={() => run("labs", "/admin/inject-labs")} disabled={!!busy}>
            <FlaskConical size={16} /> {busy === "labs" ? "Sending…" : "Inject deteriorating labs"}
          </Button>
        </Card>
        <Card title="3. Wearable simulator">
          <p className="mb-3 text-sm text-stone-600">Sync 14 more days of Apple Watch data for John (weight up, activity down).</p>
          <Button variant="secondary" onClick={() => run("days", "/admin/advance-days", { days: 14 })} disabled={!!busy}>
            <Watch size={16} /> {busy === "days" ? "Syncing…" : "Advance 14 days"}
          </Button>
        </Card>
      </div>

      {result && <pre className="max-h-60 overflow-auto rounded-xl bg-stone-900 p-4 text-xs text-stone-100">{result}</pre>}

      <Card title={<span className="flex items-center gap-2"><Activity size={16} className="text-teal-700" /> Live event stream</span>}>
        {!log.length && <p className="text-sm text-stone-500">Waiting for events…</p>}
        <ul className="space-y-1 font-mono text-xs">
          {log.map((e, i) => (
            <li key={i} className="truncate"><span className="text-stone-400">{e.at}</span> <b className="text-teal-800">{e.event}</b> {JSON.stringify(e.data).slice(0, 160)}</li>
          ))}
        </ul>
      </Card>
    </main>
  );
}
