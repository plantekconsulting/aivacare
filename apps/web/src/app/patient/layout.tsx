"use client";

import { Bell, FileUp, Home, MessageCircleHeart } from "lucide-react";
import type { ReactNode } from "react";
import { Shell, useSession } from "@/components/Shell";
import { useLive } from "@/lib/api";
import type { Notification } from "@/lib/types";

export default function PatientLayout({ children }: { children: ReactNode }) {
  const session = useSession(["patient"]);
  const { data: notes } = useLive<Notification[]>(session ? "/patient/notifications" : null, (e) => e.event === "notification");
  if (!session) return null;
  const unread = notes?.filter((n) => !n.read).length ?? 0;
  return (
    <Shell
      session={session}
      nav={[
        { href: "/patient", label: "Home", Icon: Home },
        { href: "/patient/assistant", label: "Assistant", Icon: MessageCircleHeart },
        { href: "/patient/upload", label: "Upload", Icon: FileUp },
        { href: "/patient/updates", label: "Updates", Icon: Bell, badge: unread },
      ]}
    >
      {children}
    </Shell>
  );
}
