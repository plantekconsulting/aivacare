import { fetch as streamingFetch } from "expo/fetch";
import * as SecureStore from "expo-secure-store";

const DEFAULT_API = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8710";

let apiUrl = DEFAULT_API;
let token: string | null = null;

export async function loadConfig() {
  apiUrl = (await SecureStore.getItemAsync("apiUrl")) ?? DEFAULT_API;
  token = await SecureStore.getItemAsync("token");
  return { apiUrl, signedIn: !!token };
}

export function getApiUrl() {
  return apiUrl;
}

export async function signIn(url: string, code: string) {
  apiUrl = url.replace(/\/$/, "");
  const r = await fetch(`${apiUrl}/login/john?code=${encodeURIComponent(code.trim())}`, { method: "POST" });
  if (r.status === 403) throw new Error("Invalid access code");
  if (!r.ok) throw new Error(`Login failed (${r.status})`);
  token = (await r.json()).token;
  await SecureStore.setItemAsync("apiUrl", apiUrl);
  await SecureStore.setItemAsync("token", token!);
}

export async function signOut() {
  token = null;
  await SecureStore.deleteItemAsync("token");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init.headers ?? {}) },
  });
  if (!r.ok) throw new Error(`Request failed (${r.status})`);
  return r.json();
}

export type ChatMsg = { id: string; role: "user" | "assistant"; text: string; tools: string[]; sources: { id: string; title: string; version: string }[] };

/** Streams the patient assistant (Vercel AI SDK UI message stream over SSE). */
export async function streamChat(history: ChatMsg[], onUpdate: (m: Partial<ChatMsg>) => void) {
  const body = {
    messages: history.map((m) => ({ id: m.id, role: m.role, parts: [{ type: "text", text: m.text }] })),
  };
  const res = await streamingFetch(`${apiUrl}/patient/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`Assistant unavailable (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let text = "";
  const tools = new Map<string, string>();
  const sources: ChatMsg["sources"] = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const events = buf.split("\n\n");
    buf = events.pop() ?? "";
    for (const ev of events) {
      const line = ev.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (payload === "[DONE]") continue;
      const chunk = JSON.parse(payload);
      if (chunk.type === "text-delta") text += chunk.delta;
      else if (chunk.type === "data-tool") tools.set(chunk.id, chunk.data.label + (chunk.data.status === "running" ? "…" : " ✓"));
      else if (chunk.type === "data-source") sources.push(chunk.data);
      onUpdate({ text, tools: [...tools.values()], sources: [...sources] });
    }
  }
}
