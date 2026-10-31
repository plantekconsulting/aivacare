"use client";

import { HeartPulse, LayoutDashboard, Settings2, Stethoscope } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/ui";
import { closeLive, login } from "@/lib/api";

const PERSONAS = [
  { key: "john", name: "John Miller", title: "Patient, 48 - MASLD", href: "/patient", Icon: HeartPulse, desc: "Patient portal: trends, AI assistant, report upload, care plan" },
  { key: "dr-patel", name: "Dr. Anika Patel", title: "Hepatologist", href: "/clinician", Icon: Stethoscope, desc: "Care dashboard: alert queue, Patient 360, Copilot, approvals" },
  { key: "coordinator", name: "Sam Lee, RN", title: "Care Coordinator", href: "/clinician", Icon: LayoutDashboard, desc: "Same dashboard, coordinator view" },
  { key: "admin", name: "Demo Admin", title: "Presenter controls", href: "/admin", Icon: Settings2, desc: "Reset demo, inject labs, simulate wearable days" },
];

export default function Home() {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const pick = async (p: (typeof PERSONAS)[number]) => {
    setBusy(p.key);
    setErr(null);
    try {
      closeLive();
      await login(p.key);
      router.push(p.href);
    } catch {
      setErr("Could not reach the AivaCare API.");
      setBusy(null);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-12">
      <Logo />
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-stone-900">Continuous care for fatty liver disease</h1>
      <p className="mt-2 max-w-2xl text-stone-600">
        AI agents monitor patient health between visits, give personalized, clinician-approved guidance, and bring the right
        findings to the care team - with physicians approving every clinical decision.
      </p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {PERSONAS.map((p) => (
          <button
            key={p.key}
            onClick={() => pick(p)}
            disabled={!!busy}
            className="group flex items-start gap-4 rounded-2xl border border-stone-200 bg-white p-5 text-left shadow-sm transition hover:border-teal-400 hover:shadow-md disabled:opacity-60"
          >
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-700 group-hover:bg-teal-100">
              <p.Icon size={22} />
            </div>
            <div>
              <div className="font-semibold text-stone-900">{busy === p.key ? "Signing in…" : p.name}</div>
              <div className="text-xs font-medium text-teal-800">{p.title}</div>
              <div className="mt-1 text-sm text-stone-600">{p.desc}</div>
            </div>
          </button>
        ))}
      </div>
      {err && <p className="mt-4 text-sm text-red-700">{err}</p>}
      <p className="mt-10 text-xs text-stone-500">Demonstration system - all patients and data are synthetic. Not for clinical use.</p>
    </main>
  );
}
