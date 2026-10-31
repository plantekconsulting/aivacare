"use client";

import clsx from "clsx";
import { AlertTriangle, AlertCircle, Info } from "lucide-react";
import type { ReactNode } from "react";
import type { Priority } from "@/lib/types";

export function Card({ title, action, children, className }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx("rounded-2xl border border-stone-200 bg-white p-5 shadow-sm", className)}>
      {(title || action) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-stone-800">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

const PRIORITY = {
  high: { cls: "bg-red-50 text-red-800 ring-red-200", Icon: AlertTriangle, label: "High" },
  medium: { cls: "bg-amber-50 text-amber-900 ring-amber-200", Icon: AlertCircle, label: "Medium" },
  low: { cls: "bg-sky-50 text-sky-900 ring-sky-200", Icon: Info, label: "Low" },
};

export function PriorityBadge({ p }: { p: Priority }) {
  const { cls, Icon, label } = PRIORITY[p];
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1", cls)}>
      <Icon size={12} aria-hidden /> {label}
    </span>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-teal-700 text-white hover:bg-teal-800",
        variant === "secondary" && "border border-stone-300 bg-white text-stone-800 hover:bg-stone-50",
        variant === "danger" && "bg-red-700 text-white hover:bg-red-800",
        variant === "ghost" && "text-stone-600 hover:bg-stone-100",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function slaText(due: string | null) {
  if (!due) return "";
  const ms = new Date(due).getTime() - Date.now();
  const h = Math.round(ms / 36e5);
  if (ms < 0) return `SLA breached ${Math.abs(h)}h ago`;
  return h >= 48 ? `due in ${Math.round(h / 24)}d` : `due in ${h}h`;
}

export function Logo({ small }: { small?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={clsx("grid place-items-center rounded-xl bg-teal-700 font-bold text-white", small ? "h-8 w-8 text-sm" : "h-10 w-10")}>A</div>
      <div className="leading-tight">
        <div className={clsx("font-semibold text-stone-900", small ? "text-sm" : "text-lg")}>AivaCare</div>
        <div className="text-[11px] text-stone-500">by LiverWell Clinic</div>
      </div>
    </div>
  );
}
