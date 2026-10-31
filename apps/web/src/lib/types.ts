export type Point = { date: string; value: number; source: string };
export type Metric = "ALT" | "AST" | "PLT" | "GGT" | "HBA1C" | "ALB" | "FIB4" | "WEIGHT" | "STEPS" | "RHR" | "SLEEP";

export type Hit = {
  rule_id: string;
  priority: Priority;
  title: string;
  suggested_action: string;
  metric: string;
  value: number;
  evidence: Record<string, unknown>;
};
export type Priority = "high" | "medium" | "low";

export type Review = {
  headline: string;
  summary_bullets: string[];
  suggested_actions: string[];
  rationale: string;
  sources: { id: string; title: string; section: string; version: string }[];
  generated_by: string;
};

export type Alert = {
  id: string;
  patient_id: string;
  patient_name: string;
  status: "requested" | "accepted" | "in-progress" | "completed" | "cancelled";
  priority: Priority;
  title: string;
  created: string;
  sla_due: string | null;
  hits: Hit[];
  source: string;
  ai_summary: string | null;
  proposal: { actions: string[]; rationale: string } | null;
  decision: { approved: boolean; actions: string[]; clinician: string; note?: string } | null;
};

export type Patient360 = {
  profile: { id: string; name: string; gender: string; age: number; mrn: string; conditions: string[]; medications: string[] };
  care_plan: { title: string; version: string; activities: string[]; last_updated: string };
  latest: Record<Metric, Point | null>;
  series: Record<Metric, Point[]>;
  open_alerts: Alert[];
  documents?: { id: number; filename: string; status: string; extraction: unknown; created_at: string }[];
  closed_alerts?: Alert[];
};

export type Notification = { id: number; kind: string; title: string; body: string; read: boolean; created_at: string };
