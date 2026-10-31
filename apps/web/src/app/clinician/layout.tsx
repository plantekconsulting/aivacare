"use client";

import { BellRing, Bot, ShieldCheck, Users } from "lucide-react";
import type { ReactNode } from "react";
import { Shell, useSession } from "@/components/Shell";
import { useLive } from "@/lib/api";
import type { Alert } from "@/lib/types";

export default function ClinicianLayout({ children }: { children: ReactNode }) {
  const session = useSession(["clinician", "admin"]);
  const { data: alerts } = useLive<Alert[]>(session ? "/clinician/alerts" : null, (e) => e.event.startsWith("alert") || e.event === "poll");
  if (!session) return null;
  const fresh = alerts?.filter((a) => a.status === "requested").length ?? 0;
  return (
    <Shell
      wide
      session={session}
      nav={[
        { href: "/clinician", label: "Alert queue", Icon: BellRing, badge: fresh },
        { href: "/clinician/panel", label: "Patient panel", Icon: Users },
        { href: "/clinician/copilot", label: "Copilot", Icon: Bot },
        { href: "/clinician/governance", label: "Rules & audit", Icon: ShieldCheck },
      ]}
    >
      {children}
    </Shell>
  );
}
