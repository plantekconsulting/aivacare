import { StatusBar } from "expo-status-bar";
import { type ComponentRef, useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { api, getApiUrl, loadConfig, signIn, signOut, streamChat, type ChatMsg } from "./src/api";
import { LineChart } from "./src/LineChart";

const TEAL = "#0f766e";
type Pt = { date: string; value: number; source: string };
type Home = {
  profile: { name: string };
  latest: Record<string, Pt | null>;
  series: Record<string, Pt[]>;
  care_plan: { activities: string[]; version: string };
};
type Note = { id: number; kind: string; title: string; body: string; read: boolean; created_at: string };
type Tab = "home" | "chat" | "updates";

/** Poll while the screen is mounted (mobile fallback for live updates). */
function usePoll<T>(path: string, ms = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<T>(path).then((d) => (setData(d), setError(null))).catch((e) => setError(e.message)), [path]);
  useEffect(() => {
    load();
    const t = setInterval(load, ms);
    return () => clearInterval(t);
  }, [load, ms]);
  return { data, error, load };
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [tab, setTab] = useState<Tab>("home");
  useEffect(() => {
    loadConfig().then((c) => (setSignedIn(c.signedIn), setReady(true)));
  }, []);
  if (!ready) return null;
  return (
    <SafeAreaProvider>
      <SafeAreaView style={{ flex: 1, backgroundColor: "#fafaf9" }} edges={["top", "bottom"]}>
        <StatusBar style="dark" />
        {!signedIn ? (
          <Login onDone={() => setSignedIn(true)} />
        ) : (
          <>
            <View style={s.header}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <View style={s.logo}><Text style={{ color: "white", fontWeight: "700" }}>A</Text></View>
                <View>
                  <Text style={{ fontWeight: "600", color: "#1c1917" }}>AivaCare</Text>
                  <Text style={{ fontSize: 10, color: "#78716c" }}>by LiverWell Clinic</Text>
                </View>
              </View>
              <Pressable onPress={() => signOut().then(() => setSignedIn(false))}>
                <Text style={{ color: "#78716c", fontSize: 13 }}>Sign out</Text>
              </Pressable>
            </View>
            <View style={{ flex: 1 }}>
              {tab === "home" && <HomeScreen onAsk={() => setTab("chat")} />}
              {tab === "chat" && <ChatScreen />}
              {tab === "updates" && <UpdatesScreen />}
            </View>
            <TabBar tab={tab} setTab={setTab} />
          </>
        )}
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function Login({ onDone }: { onDone: () => void }) {
  const [url, setUrl] = useState(getApiUrl());
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 24, gap: 14 }}>
      <View style={[s.logo, { width: 52, height: 52, borderRadius: 14 }]}><Text style={{ color: "white", fontWeight: "700", fontSize: 22 }}>A</Text></View>
      <Text style={{ fontSize: 26, fontWeight: "700", color: "#1c1917" }}>AivaCare</Text>
      <Text style={{ color: "#57534e" }}>Continuous care for your liver health, between every visit.</Text>
      <Text style={s.label}>Server</Text>
      <TextInput value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} style={s.input} />
      <Text style={s.label}>Team access code</Text>
      <TextInput value={code} onChangeText={setCode} secureTextEntry autoCapitalize="none" style={s.input} />
      <Pressable
        style={[s.button, busy && { opacity: 0.6 }]}
        disabled={busy}
        onPress={async () => {
          setBusy(true);
          setErr(null);
          try {
            await signIn(url, code);
            onDone();
          } catch (e) {
            setErr((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Text style={s.buttonText}>{busy ? "Signing in…" : "Continue as John Miller (demo)"}</Text>
      </Pressable>
      {err && <Text style={{ color: "#b91c1c" }}>{err}</Text>}
      <Text style={{ fontSize: 11, color: "#a8a29e", marginTop: 20 }}>Demonstration app - synthetic data only.</Text>
    </View>
  );
}

function Tile({ label, pt, unit, digits = 0, note }: { label: string; pt?: Pt | null; unit: string; digits?: number; note?: string }) {
  return (
    <View style={s.tile}>
      <Text style={s.tileLabel}>{label}</Text>
      <Text style={s.tileValue}>
        {pt ? pt.value.toFixed(digits) : "-"} <Text style={{ fontSize: 12, color: "#78716c", fontWeight: "400" }}>{unit}</Text>
      </Text>
      {note && <Text style={{ fontSize: 11, color: "#57534e" }}>{note}</Text>}
    </View>
  );
}

function fib4Note(v?: number) {
  if (v === undefined) return undefined;
  return v > 2.67 ? "● High risk" : v >= 1.3 ? "● Indeterminate" : "● Low risk";
}

function HomeScreen({ onAsk }: { onAsk: () => void }) {
  const { data, error, load } = usePoll<Home>("/patient/home", 8000);
  if (error && !data) return <Text style={{ padding: 20, color: "#b91c1c" }}>{error}</Text>;
  if (!data) return <ActivityIndicator style={{ marginTop: 40 }} color={TEAL} />;
  const { latest, series } = data;
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} refreshControl={<RefreshControl refreshing={false} onRefresh={load} />}>
      <Text style={{ fontSize: 22, fontWeight: "700", color: "#1c1917" }}>Hi {data.profile.name.split(" ")[0]}</Text>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Tile label="ALT" pt={latest.ALT} unit="U/L" note={latest.ALT && latest.ALT.value > 40 ? "● Above normal" : "● Normal"} />
        <Tile label="FIB-4" pt={latest.FIB4} unit="" digits={2} note={fib4Note(latest.FIB4?.value)} />
      </View>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Tile label="Weight" pt={latest.WEIGHT} unit="kg" digits={1} />
        <Tile label="Steps today" pt={latest.STEPS} unit="" note="Goal 8,000" />
      </View>
      <Pressable style={s.button} onPress={onAsk}><Text style={s.buttonText}>Ask about my results</Text></Pressable>
      <View style={s.card}><Text style={s.cardTitle}>ALT (U/L)</Text><LineChart points={series.ALT} goal={40} /></View>
      <View style={s.card}>
        <Text style={s.cardTitle}>FIB-4 risk score</Text>
        <LineChart points={series.FIB4} domain={[0, 4]} bands={[{ from: 0, to: 1.3, color: "#0ca30c" }, { from: 1.3, to: 2.67, color: "#fab219" }, { from: 2.67, to: 4, color: "#d03b3b" }]} />
      </View>
      <View style={s.card}><Text style={s.cardTitle}>Weight (kg) · Apple Watch</Text><LineChart points={series.WEIGHT.slice(-60)} /></View>
      <View style={s.card}><Text style={s.cardTitle}>Daily steps · Apple Watch</Text><LineChart points={series.STEPS.slice(-60)} goal={8000} /></View>
      <View style={s.card}>
        <Text style={s.cardTitle}>My care plan · {data.care_plan.version}</Text>
        {data.care_plan.activities.map((a) => <Text key={a} style={{ color: "#44403c", marginTop: 4 }}>• {a}</Text>)}
      </View>
    </ScrollView>
  );
}

const SUGGESTIONS = ["Why is my ALT high and what should I eat?", "How am I doing against my weight goal?", "My eyes look yellow today"];

function ChatScreen() {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroll = useRef<ComponentRef<typeof ScrollView>>(null);

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    const user: ChatMsg = { id: `u${Date.now()}`, role: "user", text, tools: [], sources: [] };
    const reply: ChatMsg = { id: `a${Date.now()}`, role: "assistant", text: "", tools: [], sources: [] };
    const history = [...msgs, user];
    setMsgs([...history, reply]);
    setInput("");
    setBusy(true);
    try {
      await streamChat(history, (u) => setMsgs((m) => m.map((x) => (x.id === reply.id ? { ...x, ...u } : x))));
    } catch (e) {
      setMsgs((m) => m.map((x) => (x.id === reply.id ? { ...x, text: (e as Error).message } : x)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 16, gap: 10 }} onContentSizeChange={() => scroll.current?.scrollToEnd()}>
        {msgs.length === 0 && (
          <View style={{ gap: 8, marginTop: 20 }}>
            <Text style={{ fontWeight: "600", color: "#1c1917", textAlign: "center" }}>Ask about your results, trends or care plan</Text>
            {SUGGESTIONS.map((q) => (
              <Pressable key={q} onPress={() => send(q)} style={s.suggestion}><Text style={{ color: "#134e4a", fontSize: 13 }}>{q}</Text></Pressable>
            ))}
          </View>
        )}
        {msgs.map((m) =>
          m.role === "user" ? (
            <View key={m.id} style={s.userBubble}><Text style={{ color: "white" }}>{m.text}</Text></View>
          ) : (
            <View key={m.id} style={{ gap: 6, maxWidth: "92%" }}>
              {m.tools.length > 0 && <Text style={{ fontSize: 11, color: "#78716c" }}>{m.tools.join("  ·  ")}</Text>}
              <View style={s.botBubble}>
                {m.text ? <Text style={{ color: "#1c1917", lineHeight: 20 }}>{m.text.replace(/\*\*/g, "")}</Text> : <ActivityIndicator color={TEAL} />}
              </View>
              {m.sources.map((src) => (
                <Text key={src.id} style={{ fontSize: 11, color: "#57534e" }}>📖 {src.id} {src.title} · v{src.version}</Text>
              ))}
            </View>
          ),
        )}
      </ScrollView>
      <View style={s.inputRow}>
        <TextInput value={input} onChangeText={setInput} placeholder="Ask a question…" maxLength={2000} style={[s.input, { flex: 1 }]} onSubmitEditing={() => send(input)} returnKeyType="send" />
        <Pressable style={[s.button, { paddingHorizontal: 16 }, busy && { opacity: 0.5 }]} disabled={busy} onPress={() => send(input)}>
          <Text style={s.buttonText}>Send</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function UpdatesScreen() {
  const { data } = usePoll<Note[]>("/patient/notifications", 5000);
  useEffect(() => {
    if (data?.some((n) => !n.read)) {
      const t = setTimeout(() => api("/patient/notifications/read", { method: "POST" }), 4000);
      return () => clearTimeout(t);
    }
  }, [data]);
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
      <Text style={{ fontSize: 22, fontWeight: "700", color: "#1c1917" }}>Updates</Text>
      {data?.map((n) => (
        <View key={n.id} style={[s.card, !n.read && { borderColor: "#5eead4", backgroundColor: "#f0fdfa" }]}>
          <Text style={{ fontWeight: "600", color: "#1c1917" }}>{!n.read ? "● " : ""}{n.title}</Text>
          <Text style={{ color: "#44403c", marginTop: 4, lineHeight: 20 }}>{n.body}</Text>
          <Text style={{ color: "#a8a29e", fontSize: 11, marginTop: 6 }}>{new Date(n.created_at).toLocaleString()}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function TabBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const { data } = usePoll<Note[]>("/patient/notifications", 5000);
  const unread = data?.filter((n) => !n.read).length ?? 0;
  const items: [Tab, string][] = [["home", "Home"], ["chat", "Assistant"], ["updates", unread ? `Updates (${unread})` : "Updates"]];
  return (
    <View style={s.tabbar}>
      {items.map(([k, label]) => (
        <Pressable key={k} onPress={() => setTab(k)} style={{ flex: 1, alignItems: "center", paddingVertical: 12 }}>
          <Text style={{ color: tab === k ? TEAL : "#78716c", fontWeight: tab === k ? "700" : "500" }}>{label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const s = StyleSheet.create({
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 1, borderColor: "#e7e5e4", backgroundColor: "white" },
  logo: { width: 32, height: 32, borderRadius: 9, backgroundColor: TEAL, alignItems: "center", justifyContent: "center" },
  label: { fontSize: 12, color: "#57534e", marginBottom: -8 },
  input: { borderWidth: 1, borderColor: "#d6d3d1", borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: "white", color: "#1c1917" },
  button: { backgroundColor: TEAL, borderRadius: 12, paddingVertical: 12, alignItems: "center", justifyContent: "center" },
  buttonText: { color: "white", fontWeight: "600" },
  tile: { flex: 1, backgroundColor: "white", borderRadius: 14, borderWidth: 1, borderColor: "#e7e5e4", padding: 12, gap: 2 },
  tileLabel: { fontSize: 11, color: "#78716c", fontWeight: "600", textTransform: "uppercase" },
  tileValue: { fontSize: 22, fontWeight: "700", color: "#1c1917" },
  card: { backgroundColor: "white", borderRadius: 16, borderWidth: 1, borderColor: "#e7e5e4", padding: 14 },
  cardTitle: { fontSize: 13, fontWeight: "600", color: "#292524", marginBottom: 6 },
  suggestion: { borderWidth: 1, borderColor: "#99f6e4", backgroundColor: "#f0fdfa", borderRadius: 20, paddingHorizontal: 14, paddingVertical: 9 },
  userBubble: { alignSelf: "flex-end", backgroundColor: TEAL, borderRadius: 16, borderBottomRightRadius: 4, paddingHorizontal: 14, paddingVertical: 9, maxWidth: "85%" },
  botBubble: { backgroundColor: "#f5f5f4", borderRadius: 16, borderBottomLeftRadius: 4, paddingHorizontal: 14, paddingVertical: 10 },
  inputRow: { flexDirection: "row", gap: 8, padding: 10, borderTopWidth: 1, borderColor: "#e7e5e4", backgroundColor: "white" },
  tabbar: { flexDirection: "row", borderTopWidth: 1, borderColor: "#e7e5e4", backgroundColor: "white" },
});
