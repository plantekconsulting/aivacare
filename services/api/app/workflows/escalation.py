"""Escalation workflow (LangGraph): rule hit -> FHIR Task -> AI review -> clinician approval (interrupt) -> apply + follow-up.

State is checkpointed in Postgres, so a pending approval survives restarts.
"""
import asyncio
import json
import logging
import uuid
from typing import TypedDict

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .. import clinical, db, fhir
from ..agents import copilot

log = logging.getLogger("escalation")


class EscalationState(TypedDict, total=False):
    patient_id: str
    hits: list[dict]
    source: str
    task_id: str
    review: dict
    decision: dict


async def open_task(state: EscalationState, config) -> dict:
    view = await clinical.create_task(state["patient_id"], state["hits"], config["configurable"]["thread_id"], state.get("source", "rules-engine"))
    return {"task_id": view["id"]}


async def ai_review(state: EscalationState) -> dict:
    review = await copilot.review_alert(state["patient_id"], state["hits"])
    await clinical.update_task(state["task_id"], outputs={
        "ai_summary": json.dumps(review),
        "ai_proposal": json.dumps({"actions": review["suggested_actions"], "rationale": review["rationale"]}),
    })
    await db.audit("clinician-copilot", "alert.reviewed", {"task_id": state["task_id"], "model": review["generated_by"]})
    return {"review": review}


async def await_clinician(state: EscalationState) -> dict:
    decision = interrupt({"task_id": state["task_id"], "awaiting": "clinician_approval"})
    return {"decision": decision}


async def apply_decision(state: EscalationState) -> dict:
    d, pid, task_id = state["decision"], state["patient_id"], state["task_id"]
    if not d.get("approved"):
        await clinical.update_task(task_id, status="cancelled", outputs={"decision": json.dumps(d)})
        await db.audit(d["clinician"], "alert.dismissed", {"task_id": task_id, "note": d.get("note")})
        return {}

    actions = d["actions"]
    cp = await fhir.read("CarePlan", f"{pid}-careplan")
    version = int(cp.get("note", [{"text": "version 1"}])[0]["text"].split()[-1]) + 1
    cp["activity"] = [{"detail": {"status": "scheduled", "description": a}} for a in actions] + cp.get("activity", [])
    cp["note"] = [{"text": f"version {version}"}]
    await fhir.update(cp)
    await clinical.update_task(task_id, status="completed", outputs={"decision": json.dumps(d)})
    await db.audit(d["clinician"], "careplan.approved", {"task_id": task_id, "actions": actions, "careplan_version": version})

    profile = await clinical.patient_profile(pid)
    message = await copilot.compose_followup(profile["name"].split()[0], actions, d["clinician"])
    await clinical.notify(pid, "followup", "Update from your care team", message)
    return {}


def _build() -> StateGraph:
    g = StateGraph(EscalationState)
    g.add_node("open_task", open_task)
    g.add_node("ai_review", ai_review)
    g.add_node("await_clinician", await_clinician)
    g.add_node("apply_decision", apply_decision)
    g.add_edge(START, "open_task")
    g.add_edge("open_task", "ai_review")
    g.add_edge("ai_review", "await_clinician")
    g.add_edge("await_clinician", "apply_decision")
    g.add_edge("apply_decision", END)
    return g


_graph = None
_background: set[asyncio.Task] = set()


async def init() -> None:
    global _graph
    saver = AsyncPostgresSaver(db.pool)
    await saver.setup()
    _graph = _build().compile(checkpointer=saver)


def _spawn(coro) -> None:
    t = asyncio.create_task(coro)
    _background.add(t)
    t.add_done_callback(_background.discard)


async def _run(payload, thread_id: str) -> None:
    try:
        await _graph.ainvoke(payload, {"configurable": {"thread_id": thread_id}})
    except Exception:
        log.exception("escalation workflow failed (thread %s)", thread_id)


def start(patient_id: str, hits: list[dict], source: str = "rules-engine") -> str:
    """Kick off an escalation in the background; returns the workflow thread id."""
    thread_id = f"esc-{uuid.uuid4().hex[:12]}"
    _spawn(_run({"patient_id": patient_id, "hits": hits, "source": source}, thread_id))
    return thread_id


async def resume(thread_id: str, decision: dict) -> None:
    await _graph.ainvoke(Command(resume=decision), {"configurable": {"thread_id": thread_id}})
