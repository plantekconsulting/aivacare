"""Clinician care dashboard API."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import clinical, db
from ..agents import runtime
from ..agents.prompts import CLINICIAN_SYSTEM
from ..auth import User, require
from ..mcp_servers import SourceRegistry, clinician_gateway
from ..rules.engine import CATALOG
from ..workflows import escalation
from .chat_stream import history_from_ui, rate_limit, ui_stream

router = APIRouter(prefix="/clinician")
Clinician = Depends(require("clinician", "admin"))


@router.get("/panel")
async def panel(user: User = Clinician) -> list[dict]:
    names = await clinical.patient_names()
    tasks = await clinical.list_tasks()
    rank = {"high": 3, "medium": 2, "low": 1}
    out = []
    for pid, name in names.items():
        mine = [t for t in tasks if t["patient_id"] == pid]
        fib4 = await clinical.trend(pid, "FIB4", 400)
        alt = await clinical.trend(pid, "ALT", 400)
        top = max((rank[t["priority"]] for t in mine), default=0)
        out.append({
            "patient_id": pid, "name": name, "open_alerts": len(mine),
            "top_priority": {3: "high", 2: "medium", 1: "low", 0: None}[top],
            "fib4": fib4[-1]["value"] if fib4 else None, "fib4_prev": fib4[-2]["value"] if len(fib4) > 1 else None,
            "alt": alt[-1]["value"] if alt else None, "last_lab": alt[-1]["date"][:10] if alt else None,
        })
    return sorted(out, key=lambda p: (-rank.get(p["top_priority"], 0), -(p["fib4"] or 0)))


@router.get("/alerts")
async def alerts(include_closed: bool = False, user: User = Clinician) -> list[dict]:
    return await clinical.list_tasks(include_closed=include_closed)


@router.get("/patients/{pid}")
async def patient(pid: str, user: User = Clinician) -> dict:
    if pid not in await clinical.patient_names():
        raise HTTPException(404, "Patient not in panel")
    data = await clinical.patient_360(pid)
    data["documents"] = await db.fetch(
        "SELECT id, filename, status, extraction, created_at FROM uploads WHERE patient_id = %s ORDER BY created_at DESC", pid)
    data["closed_alerts"] = [t for t in await clinical.list_tasks(patient_id=pid, include_closed=True)
                             if t["status"] in ("completed", "cancelled")]
    return data


@router.post("/alerts/{task_id}/acknowledge")
async def acknowledge(task_id: str, user: User = Clinician) -> dict:
    view = await clinical.update_task(task_id, status="accepted")
    await db.audit(user.name, "alert.acknowledged", {"task_id": task_id})
    return view


class Decision(BaseModel):
    approved: bool
    actions: list[str] = []
    note: str | None = None


@router.post("/alerts/{task_id}/decision")
async def decide(task_id: str, d: Decision, user: User = Clinician) -> dict:
    task = await clinical.get_task(task_id)
    if task["status"] in ("completed", "cancelled"):
        raise HTTPException(409, "Alert already closed")
    if d.approved and not d.actions:
        raise HTTPException(400, "Select at least one action to approve")
    await escalation.resume(task["thread_id"], {**d.model_dump(), "clinician": user.name})
    return await clinical.get_task(task_id)


@router.post("/chat")
async def chat(body: dict, user: User = Clinician):
    rate_limit(user.sub)
    history = history_from_ui(body.get("messages", []))
    if not history or history[-1]["role"] != "user":
        raise HTTPException(400, "No question received")
    context = body.get("patient_id")
    registry = SourceRegistry()
    system = CLINICIAN_SYSTEM + f"\n\nToday is {date.today().isoformat()}. Signed in: {user.name}."
    if context:
        system += f"\nThe clinician is currently viewing patient_id={context}; assume questions refer to this patient unless stated."
    await db.audit(user.name, "copilot.message", {"patient_id": context})
    events = runtime.run_agent(system, history, clinician_gateway(user, registry), effort="medium")
    return ui_stream(events, lambda: registry.sources)


@router.get("/rules")
async def rules(user: User = Clinician) -> dict:
    return CATALOG


@router.get("/audit")
async def audit(user: User = Clinician) -> list[dict]:
    return await db.fetch("SELECT actor, action, detail, created_at FROM audit_log ORDER BY created_at DESC LIMIT 100")
