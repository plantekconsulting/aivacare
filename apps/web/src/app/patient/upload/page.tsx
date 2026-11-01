"use client";

import { AlertTriangle, CheckCircle2, FileText, Loader2, Upload } from "lucide-react";
import { useState } from "react";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

type Row = { test_name: string; key: string; value: number; unit: string; reference_range: string | null; status: string };
type Extraction = { upload_id: number; patient_name: string | null; collection_date: string | null; lab_name: string | null; results: Row[]; warnings: string[] };

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<"idle" | "reading" | "review" | "saving" | "done">("idle");
  const [ext, setExt] = useState<Extraction | null>(null);
  const [saved, setSaved] = useState<{ saved: number; new_alerts: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const read = async () => {
    if (!file) return;
    setErr(null);
    setStage("reading");
    const fd = new FormData();
    fd.append("file", file);
    try {
      setExt(await api<Extraction>("/patient/documents", { method: "POST", body: fd }));
      setStage("review");
    } catch (e) {
      setErr((e as Error).message);
      setStage("idle");
    }
  };

  const confirm = async () => {
    if (!ext) return;
    setStage("saving");
    try {
      setSaved(await api(`/patient/documents/${ext.upload_id}/confirm`, { method: "POST" }));
      setStage("done");
    } catch (e) {
      setErr((e as Error).message);
      setStage("review");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-stone-900">Upload a lab report</h1>
        <p className="text-sm text-stone-600">AI reads your report, you check the values, and they're added to your record for your care team.</p>
      </div>

      <Card>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-stone-300 bg-stone-50 px-6 py-10 text-center hover:border-teal-500">
          <Upload className="text-teal-700" />
          <span className="text-sm font-medium text-stone-800">{file ? file.name : "Choose a PDF or photo of your report"}</span>
          <span className="text-xs text-stone-500">PDF, PNG or JPEG up to 15 MB</span>
          <input type="file" accept="application/pdf,image/png,image/jpeg" className="hidden" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setStage("idle"); setExt(null); setSaved(null); }} />
        </label>
        <div className="mt-4 flex items-center justify-between gap-3">
          <a href="/samples/john-miller-liver-panel.pdf" download className="text-xs text-teal-800 underline">
            No report handy? Download a sample (synthetic)
          </a>
          <Button onClick={read} disabled={!file || stage === "reading"}>
            {stage === "reading" ? <><Loader2 size={16} className="animate-spin" /> Reading report…</> : <><FileText size={16} /> Read report</>}
          </Button>
        </div>
      </Card>

      {err && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">{err}</div>}

      {ext && stage !== "idle" && (
        <Card title="Please check these values" action={<span className="text-xs text-stone-500">{ext.lab_name} · collected {ext.collection_date ?? "unknown"}</span>}>
          {ext.warnings.map((w) => (
            <div key={w} className="mb-2 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" /> {w}
            </div>
          ))}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-stone-200 text-left text-xs uppercase text-stone-500">
                  <th className="py-2">Test</th><th>Value</th><th>Reference</th><th>Will save</th>
                </tr>
              </thead>
              <tbody>
                {ext.results.map((r) => (
                  <tr key={r.test_name} className="border-b border-stone-100">
                    <td className="py-2 text-stone-800">{r.test_name}</td>
                    <td className="tabular-nums">{r.value} {r.unit}</td>
                    <td className="text-stone-500">{r.reference_range ?? "-"}</td>
                    <td>{r.status === "ok" ? <CheckCircle2 size={16} className="text-green-700" aria-label="yes" /> : <span className="text-xs text-stone-500">{r.status === "not_tracked" ? "not tracked" : "needs review"}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {stage !== "done" ? (
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setExt(null); setStage("idle"); }}>Discard</Button>
              <Button onClick={confirm} disabled={stage === "saving"}>{stage === "saving" ? "Saving…" : "These values are correct - save"}</Button>
            </div>
          ) : (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-900">
              <CheckCircle2 size={16} /> Saved {saved?.saved} values to your record (linked to this document).
              {!!saved?.new_alerts && " Your care team has been notified to review them."}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
