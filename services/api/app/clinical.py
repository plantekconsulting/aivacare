"""Clinical service layer shared by MCP tools, API routes and the escalation workflow."""
import json
from datetime import date, datetime, timedelta, timezone

from . import db, events, fhir
from .rules import engine

PRIORITY_TO_FHIR = {"high": "asap", "medium": "urgent", "low": "routine"}
FHIR_TO_PRIORITY = {v: k for k, v in PRIORITY_TO_FHIR.items()}
OPEN_STATUSES = "requested,accepted,in-progress"
WORKFLOW_SYSTEM = "https://aivacare.dev/workflow-thread"


def _age(birth: str) -> int:
    b = date.fromisoformat(birth)
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def _name(p: dict) -> str:
    n = p["name"][0]
    return f"{' '.join(n.get('given', []))} {n.get('family', '')}".strip()


async def patient_profile(pid: str) -> dict:
    p = await fhir.read("Patient", pid)
    conditions = await fhir.search("Condition", {"subject": f"Patient/{pid}"})
    meds = await fhir.search("MedicationStatement", {"subject": f"Patient/{pid}", "status": "active"})
    return {
        "id": pid, "name": _name(p), "gender": p.get("gender"), "age": _age(p["birthDate"]),
        "mrn": p.get("identifier", [{}])[0].get("value"),
        "conditions": [c["code"]["text"] for c in conditions],
        "medications": [m["medicationCodeableConcept"]["text"] for m in meds],
    }


async def care_plan(pid: str) -> dict:
    cp = await fhir.read("CarePlan", f"{pid}-careplan")
    return {
        "title": cp.get("title"),
        "version": (cp.get("note") or [{"text": "version 1"}])[0]["text"],
        "activities": [a["detail"]["description"] for a in cp.get("activity", [])],
        "last_updated": cp.get("meta", {}).get("lastUpdated"),
    }


async def trend(pid: str, metric: str, days: int = 365) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    return await fhir.observations(pid, metric.upper(), since)


async def all_series(pid: str, days: int = 400) -> dict[str, list[dict]]:
    return {k: await trend(pid, k, days) for k in fhir.LOINC}


async def patient_360(pid: str) -> dict:
    series = await all_series(pid)
    latest = {k: (v[-1] if v else None) for k, v in series.items()}
    return {
        "profile": await patient_profile(pid),
        "care_plan": await care_plan(pid),
        "latest": latest,
        "series": series,
        "open_alerts": await list_tasks(patient_id=pid),
    }


# ---------------------------------------------------------------- rules + escalation tasks

async def evaluate_rules(pid: str) -> list[dict]:
    series = await all_series(pid)
    return [h.to_dict() for h in engine.evaluate(series)]


def task_view(t: dict, names: dict[str, str] | None = None) -> dict:
    io = {i["type"]["text"]: i["valueString"] for i in t.get("input", []) + t.get("output", [])}
    pid = t["for"]["reference"].split("/")[1]
    return {
        "id": t["id"],
        "patient_id": pid,
        "patient_name": (names or {}).get(pid, pid),
        "status": t["status"],
        "priority": FHIR_TO_PRIORITY.get(t.get("priority"), "low"),
        "title": t.get("description"),
        "created": t.get("authoredOn"),
        "sla_due": t.get("restriction", {}).get("period", {}).get("end"),
        "hits": json.loads(io.get("rule_hits", "[]")),
        "source": io.get("source", "rules-engine"),
        "ai_summary": io.get("ai_summary"),
        "proposal": json.loads(io["ai_proposal"]) if io.get("ai_proposal") else None,
        "decision": json.loads(io["decision"]) if io.get("decision") else None,
        "thread_id": next((i["value"] for i in t.get("identifier", []) if i["system"] == WORKFLOW_SYSTEM), None),
    }


async def patient_names() -> dict[str, str]:
    return {p["id"]: _name(p) for p in await fhir.search("Patient", {"_count": "200", "_elements": "name"})}


async def list_tasks(patient_id: str | None = None, include_closed: bool = False) -> list[dict]:
    params = {"_sort": "-authored-on", "_count": "100"}
    if not include_closed:
        params["status"] = OPEN_STATUSES
    if patient_id:
        params["patient"] = f"Patient/{patient_id}"
    tasks = await fhir.search("Task", params)
    names = await patient_names()
    views = [task_view(t, names) for t in tasks]
    rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(views, key=lambda v: (rank[v["priority"]], v["sla_due"] or ""))


async def get_task(task_id: str) -> dict:
    return task_view(await fhir.read("Task", task_id), await patient_names())


async def create_task(pid: str, hits: list[dict], thread_id: str, source: str = "rules-engine") -> dict:
    top = max(hits, key=lambda h: engine.PRIORITY_RANK[h["priority"]])
    now = datetime.now(timezone.utc)
    due = now + timedelta(hours=engine.SLA_HOURS[top["priority"]])
    task = {
        "resourceType": "Task", "status": "requested", "intent": "order",
        "priority": PRIORITY_TO_FHIR[top["priority"]],
        "code": {"text": "Clinical review"},
        "description": top["title"] if len(hits) == 1 else f"{top['title']} (+{len(hits) - 1} more)",
        "for": {"reference": f"Patient/{pid}"},
        "owner": {"reference": "Practitioner/dr-anika-patel"},
        "authoredOn": now.isoformat(timespec="seconds"),
        "restriction": {"period": {"end": due.isoformat(timespec="seconds")}},
        "identifier": [{"system": WORKFLOW_SYSTEM, "value": thread_id}],
        "input": [
            {"type": {"text": "rule_hits"}, "valueString": json.dumps(hits)},
            {"type": {"text": "source"}, "valueString": source},
        ],
    }
    created = await fhir.create(task)
    view = await get_task(created["id"])
    await db.audit("rules-engine", "task.created", {"task_id": created["id"], "patient_id": pid, "rules": [h["rule_id"] for h in hits]})
    events.publish("alert.created", view, clinicians=True)
    return view


async def update_task(task_id: str, *, status: str | None = None, outputs: dict[str, str] | None = None) -> dict:
    t = await fhir.read("Task", task_id)
    if status:
        t["status"] = status
    if outputs:
        existing = {o["type"]["text"]: o for o in t.get("output", [])}
        for k, v in outputs.items():
            existing[k] = {"type": {"text": k}, "valueString": v}
        t["output"] = list(existing.values())
    await fhir.update(t)
    view = await get_task(task_id)
    events.publish("alert.updated", view, clinicians=True)
    return view


async def open_rule_ids(pid: str) -> set[str]:
    return {h["rule_id"] for t in await list_tasks(patient_id=pid) for h in t["hits"]}


# ---------------------------------------------------------------- data ingestion (event-driven entry point)

async def ingest_observations(pid: str, obs: list[dict], actor: str) -> list[dict]:
    """Persist observations, derive FIB-4 for complete lab panels, then run rules. Returns new rule hits."""
    keys = {fhir.CODE_TO_KEY.get(o["code"]["coding"][0]["code"]): o for o in obs}
    if {"ALT", "AST", "PLT"} <= keys.keys():
        profile = await patient_profile(pid)
        score = engine.fib4(profile["age"], keys["AST"]["valueQuantity"]["value"],
                            keys["ALT"]["valueQuantity"]["value"], keys["PLT"]["valueQuantity"]["value"])
        obs = obs + [fhir.observation(pid, "FIB4", score, keys["ALT"]["effectiveDateTime"], source="rules-engine")]
    await fhir.transaction([{"resource": o, "request": {"method": "POST", "url": "Observation"}} for o in obs])
    await db.audit(actor, "observations.ingested", {"patient_id": pid, "count": len(obs)})
    events.publish("data.updated", {"patient_id": pid}, patient_id=pid, clinicians=True)

    already = await open_rule_ids(pid)
    return [h for h in await evaluate_rules(pid) if h["rule_id"] not in already]


# ---------------------------------------------------------------- notifications

async def notify(pid: str, kind: str, title: str, body: str) -> None:
    await db.execute("INSERT INTO notifications (patient_id, kind, title, body) VALUES (%s, %s, %s, %s)", pid, kind, title, body)
    events.publish("notification", {"kind": kind, "title": title, "body": body}, patient_id=pid)


async def notifications(pid: str) -> list[dict]:
    return await db.fetch(
        "SELECT id, kind, title, body, read, created_at FROM notifications WHERE patient_id = %s ORDER BY created_at DESC LIMIT 50", pid
    )
