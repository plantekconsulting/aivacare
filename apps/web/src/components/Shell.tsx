"use client";

import clsx from "clsx";
import { LogOut, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { closeLive, getSession, setSession, type Session } from "@/lib/api";
import { Logo } from "./ui";

export type NavItem = { href: string; label: string; Icon: LucideIcon; badge?: number };

export function useSession(role: Session["role"][]) {
  const router = useRouter();
  const [s, setS] = useState<Session | null>(null);
  useEffect(() => {
    const cur = getSession();
    if (!cur || !role.includes(cur.role)) router.replace("/");
    else setS(cur);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return s;
}

export function Shell({ nav, children, session, wide }: { nav: NavItem[]; children: ReactNode; session: Session; wide?: boolean }) {
  const path = usePathname();
  const router = useRouter();
  const signOut = () => {
    closeLive();
    setSession(null);
    router.push("/");
  };
  const active = (href: string) => (href === nav[0].href ? path === href : path.startsWith(href));

  return (
    <div className="min-h-screen pb-20 md:pb-0">
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/90 backdrop-blur">
        <div className={clsx("mx-auto flex items-center justify-between gap-4 px-4 py-3", wide ? "max-w-[1400px]" : "max-w-5xl")}>
          <Logo small />
          <nav className="hidden gap-1 md:flex">
            {nav.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={clsx(
                  "relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
                  active(n.href) ? "bg-teal-50 font-medium text-teal-800" : "text-stone-600 hover:bg-stone-100",
                )}
              >
                <n.Icon size={16} /> {n.label}
                {!!n.badge && <span className="rounded-full bg-red-600 px-1.5 text-[10px] font-semibold text-white">{n.badge}</span>}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-stone-600 sm:inline">{session.name}</span>
            <button onClick={signOut} className="rounded-lg p-2 text-stone-500 hover:bg-stone-100" aria-label="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>
      <main className={clsx("mx-auto px-4 py-6", wide ? "max-w-[1400px]" : "max-w-5xl")}>{children}</main>
      <nav className="fixed inset-x-0 bottom-0 z-20 flex border-t border-stone-200 bg-white md:hidden">
        {nav.map((n) => (
          <Link key={n.href} href={n.href} className={clsx("relative flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px]", active(n.href) ? "text-teal-800" : "text-stone-500")}>
            <n.Icon size={20} />
            {n.label}
            {!!n.badge && <span className="absolute right-1/4 top-1 h-2 w-2 rounded-full bg-red-600" />}
          </Link>
        ))}
      </nav>
    </div>
  );
}
