"use client";

import { useEffect, useRef, useState } from "react";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8710";

export type Session = { token: string; role: "patient" | "clinician" | "admin"; name: string; sub: string; can_approve?: boolean };

const KEY = "aivacare.session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function setSession(s: Session | null) {
  if (s) localStorage.setItem(KEY, JSON.stringify(s));
  else localStorage.removeItem(KEY);
}

export const getAccessCode = () => (typeof window === "undefined" ? "" : localStorage.getItem("aivacare.code") ?? "");
export const setAccessCode = (c: string) => localStorage.setItem("aivacare.code", c);

export async function login(persona: string): Promise<Session> {
  const r = await fetch(`${API_URL}/login/${persona}?code=${encodeURIComponent(getAccessCode())}`, { method: "POST" });
  if (r.status === 403) throw new Error("Invalid access code");
  if (r.status === 429) throw new Error("Too many attempts - try again in 15 minutes.");
  if (!r.ok) throw new Error("Could not reach the AivaCare API.");
  const s = (await r.json()) as Session;
  setSession(s);
  return s;
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const s = getSession();
  const headers = new Headers(init.headers);
  if (s) headers.set("Authorization", `Bearer ${s.token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const r = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (r.status === 401 && typeof window !== "undefined") {
    setSession(null);
    window.location.href = "/";
  }
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${r.status})`);
  }
  return r.json() as Promise<T>;
}

/** Loads data and re-loads it whenever a live event arrives (SSE, with polling fallback). */
export function useLive<T>(path: string | null, eventFilter?: (e: LiveEvent) => boolean) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterRef = useRef(eventFilter);
  filterRef.current = eventFilter;

  useEffect(() => {
    if (!path) return;
    let alive = true;
    const load = () =>
      api<T>(path)
        .then((d) => alive && (setData(d), setError(null)))
        .catch((e) => alive && setError(String(e.message ?? e)));
    load();
    const unsubscribe = onLiveEvent((e) => {
      if (!filterRef.current || filterRef.current(e)) load();
    });
    return () => {
      alive = false;
      unsubscribe();
    };
  }, [path]);

  return { data, error, reload: () => path && api<T>(path).then(setData) };
}

export type LiveEvent = { event: string; data: Record<string, unknown> };
type Listener = (e: LiveEvent) => void;
const listeners = new Set<Listener>();
let source: EventSource | null = null;
let pollTimer: ReturnType<typeof setInterval> | null = null;

function ensureStream() {
  const s = getSession();
  if (!s || source) return;
  source = new EventSource(`${API_URL}/events?token=${encodeURIComponent(s.token)}`);
  source.onmessage = (m) => {
    const e = JSON.parse(m.data) as LiveEvent;
    listeners.forEach((l) => l(e));
  };
  source.onopen = () => {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
  };
  source.onerror = () => {
    // Fallback: poll every 5s while the stream is down (some proxies block SSE).
    if (!pollTimer) pollTimer = setInterval(() => listeners.forEach((l) => l({ event: "poll", data: {} })), 5000);
  };
}

export function onLiveEvent(l: Listener) {
  listeners.add(l);
  ensureStream();
  return () => {
    listeners.delete(l);
    if (!listeners.size && source) {
      source.close();
      source = null;
    }
  };
}

export function closeLive() {
  source?.close();
  source = null;
}
