"""MCP tool layer: the only way agents reach data or take actions.

Five FastMCP servers (fhir, knowledge, insights, workflow, document) are composed into a
role-specific gateway per request. Identity is bound into the server at construction time from
the signed-in user's token - patient tools have no patient_id parameter, so a prompt cannot
ask for someone else's record.
"""
import json
from statistics import mean
from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from . import clinical, db, rag
from .auth import User

Metric = Literal["ALT", "AST", "PLT", "GGT", "HBA1C", "ALB", "FIB4", "WEIGHT", "STEPS", "RHR", "SLEEP"]


class SourceRegistry:
    """Collects knowledge sources retrieved during a turn so the UI can render citations."""

    def __init__(self) -> None:
        self.sources: list[dict] = []

    def add(self, row: dict) -> str:
        for s in self.sources:
            if s["chunk_id"] == row["id"]:
                return s["id"]
        sid = f"S{len(self.sources) + 1}"
        self.sources.append({
            "id": sid, "chunk_id": row["id"], "title": row["title"], "section": row["section"],
            "version": row["version"], "approved_by": row["approved_by"], "excerpt": row["content"][:280],
        })
        return sid


def symptom_hit(description: str, priority: str) -> dict:
    return {
        "rule_id": "patient_reported_symptom", "priority": priority,
        "title": f"Patient-reported symptom: {description[:80]}",
        "suggested_action": "Contact patient today; assess for decompensation.",
        "metric": "SYMPTOM", "value": 0, "threshold": 0, "evidence": {"reported": description[:500]},
    }


def _compact(points: list[dict], limit: int = 40) -> list[dict]:
    pts = points[-limit:]
    return [{"date": p["date"][:10], "value": p["value"], "source": p["source"]} for p in pts]


def _knowledge_server(audiences: list[str], registry: SourceRegistry) -> FastMCP:
    s = FastMCP("knowledge")

    @s.tool
    async def search_guidance(query: Annotated[str, Field(description="What to look up, in plain words")]) -> str:
        """Search LiverWell's clinician-approved knowledge base. Returns excerpts tagged with source ids
        like [S1]. Use only these excerpts for medical guidance and cite them by id."""
        rows = await rag.search(query, audiences)
        if not rows:
            return "NO_APPROVED_CONTENT: nothing in the approved knowledge base matches this question."
        return "\n\n".join(f"[{registry.add(r)}] {r['title']} - {r['section']}:\n{r['content']}" for r in rows)

    return s


# ------------------------------------------------------------------ patient gateway

def patient_gateway(user: User, registry: SourceRegistry) -> FastMCP:
    pid = user.sub

    fhir_s = FastMCP("fhir")

    @fhir_s.tool
    async def get_my_profile() -> dict:
        """The signed-in patient's demographics, conditions and active medications."""
        return await clinical.patient_profile(pid)

    @fhir_s.tool
    async def get_my_trend(metric: Metric, days: Annotated[int, Field(ge=7, le=400)] = 180) -> dict:
        """Exact values over time for one metric from the patient's record (labs from the EHR, wearable data
        from Apple Watch). ALT/AST/GGT in U/L, PLT 10^3/uL, HBA1C %, WEIGHT kg, STEPS per day, RHR bpm, SLEEP hours."""
        return {"metric": metric, "points": _compact(await clinical.trend(pid, metric, days))}

    @fhir_s.tool
    async def get_my_latest_results() -> dict:
        """Most recent value of every lab and wearable metric, with dates."""
        series = await clinical.all_series(pid)
        return {k: (v[-1] if v else None) for k, v in series.items()}

    @fhir_s.tool
    async def get_my_care_plan() -> dict:
        """The patient's current care plan activities and goals."""
        return await clinical.care_plan(pid)

    insights = FastMCP("insights")

    @insights.tool
    async def get_my_progress() -> dict:
        """Progress against care-plan goals: weight change from start, recent activity vs. the 8,000 step goal, sleep."""
        series = await clinical.all_series(pid)
        w, steps, sleep = series["WEIGHT"], series["STEPS"], series["SLEEP"]
        recent = [p["value"] for p in steps[-7:]]
        return {
            "weight_start_kg": w[0]["value"] if w else None, "weight_now_kg": w[-1]["value"] if w else None,
            "weight_change_pct": round((w[-1]["value"] - w[0]["value"]) / w[0]["value"] * 100, 1) if w else None,
            "avg_steps_last_7_days": round(mean(recent)) if recent else None, "step_goal": 8000,
            "avg_sleep_last_7_days": round(mean(p["value"] for p in sleep[-7:]), 1) if sleep else None,
        }

    workflow = FastMCP("workflow")

    @workflow.tool
    async def log_symptom(description: str, severity: Literal["mild", "moderate", "severe"]) -> str:
        """Record a symptom the patient reports so the care team can see it."""
        await db.audit(pid, "symptom.logged", {"description": description, "severity": severity})
        if severity == "severe":
            from .workflows import escalation

            escalation.start(pid, [symptom_hit(description, "high")], source="patient-report")
            return "Logged and flagged to the care team for same-day follow-up."
        return "Logged for the care team."

    @workflow.tool
    async def request_appointment(reason: str, timeframe: Literal["this week", "next 2 weeks", "next month"]) -> str:
        """Ask the care coordinator to schedule an appointment. Does not book directly."""
        await db.audit(pid, "appointment.requested", {"reason": reason, "timeframe": timeframe})
        await clinical.notify(pid, "info", "Appointment request sent", f"The care coordinator will contact you to schedule ({timeframe}).")
        return "Request sent to the care coordinator."

    document = FastMCP("document")

    @document.tool
    async def list_my_documents() -> list[dict]:
        """Medical reports the patient has uploaded and their extraction status."""
        return await db.fetch("SELECT id, filename, status, created_at FROM uploads WHERE patient_id = %s ORDER BY created_at DESC", pid)

    gw = FastMCP("aivacare-patient")
    for name, server in [("fhir", fhir_s), ("knowledge", _knowledge_server(["patient"], registry)),
                         ("insights", insights), ("workflow", workflow), ("document", document)]:
        gw.mount(server, namespace=name)
    return gw


# ------------------------------------------------------------------ clinician gateway

async def _panel() -> dict[str, str]:
    return await clinical.patient_names()


def clinician_gateway(user: User, registry: SourceRegistry) -> FastMCP:
    async def check(patient_id: str) -> None:
        if patient_id not in await _panel():
            raise ValueError(f"Patient {patient_id} is not in your assigned panel")

    fhir_s = FastMCP("fhir")

    @fhir_s.tool
    async def list_patient_panel() -> list[dict]:
        """Patients assigned to this clinician (id and name)."""
        return [{"patient_id": k, "name": v} for k, v in (await _panel()).items()]

    @fhir_s.tool
    async def get_patient_summary(patient_id: str) -> dict:
        """Profile, care plan and latest value of every metric for one patient."""
        await check(patient_id)
        data = await clinical.patient_360(patient_id)
        data.pop("series")
        return data

    @fhir_s.tool
    async def get_trend(patient_id: str, metric: Metric, days: Annotated[int, Field(ge=7, le=400)] = 180) -> dict:
        """Exact time series for one metric for one patient."""
        await check(patient_id)
        return {"metric": metric, "points": _compact(await clinical.trend(patient_id, metric, days))}

    insights = FastMCP("insights")

    @insights.tool
    async def get_risk_flags(patient_id: str) -> list[dict]:
        """Deterministic rule-engine findings for a patient (FIB-4 bands, ALT vs baseline, wearable trends)."""
        await check(patient_id)
        return await clinical.evaluate_rules(patient_id)

    workflow = FastMCP("workflow")

    @workflow.tool
    async def list_open_alerts() -> list[dict]:
        """Open escalation tasks across the panel, highest priority first."""
        return [{k: t[k] for k in ("id", "patient_id", "patient_name", "priority", "status", "title", "sla_due")}
                for t in await clinical.list_tasks()]

    @workflow.tool
    async def propose_careplan_change(task_id: str, actions: list[str], rationale: str) -> str:
        """Draft care-plan actions for an alert. This only creates a PROPOSAL - nothing changes until the
        clinician presses Approve in the dashboard."""
        await clinical.update_task(task_id, outputs={"ai_proposal": json.dumps({"actions": actions, "rationale": rationale})})
        await db.audit(user.sub, "careplan.proposed", {"task_id": task_id, "actions": actions})
        return "Proposal attached to the alert and awaiting clinician approval."

    document = FastMCP("document")

    @document.tool
    async def list_patient_documents(patient_id: str) -> list[dict]:
        """Reports a patient uploaded, with extracted values."""
        await check(patient_id)
        return await db.fetch("SELECT id, filename, status, extraction, created_at FROM uploads WHERE patient_id = %s", patient_id)

    gw = FastMCP("aivacare-clinician")
    for name, server in [("fhir", fhir_s), ("knowledge", _knowledge_server(["clinician", "patient"], registry)),
                         ("insights", insights), ("workflow", workflow), ("document", document)]:
        gw.mount(server, namespace=name)
    return gw
