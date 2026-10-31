"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { closeLive, login, setAccessCode } from "@/lib/api";

/** Deep link for presenters: /go?as=dr-patel&next=/clinician */
function Go() {
  const params = useSearchParams();
  const router = useRouter();
  useEffect(() => {
    const persona = params.get("as") ?? "john";
    const next = params.get("next") ?? "/";
    closeLive();
    const code = params.get("code");
    if (code) setAccessCode(code);
    login(persona)
      .then(() => router.replace(next.startsWith("/") ? next : "/"))
      .catch(() => router.replace("/"));
  }, [params, router]);
  return <p className="p-8 text-sm text-stone-500">Signing in…</p>;
}

export default function GoPage() {
  return (
    <Suspense>
      <Go />
    </Suspense>
  );
}
