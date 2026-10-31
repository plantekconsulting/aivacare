"""Single-shot AI tools: alert review (summarize_patient + explain_alert) and patient follow-up (compose_nudge)."""
import json

import anthropic
from pydantic import BaseModel, Field

from .. import clinical, rag
from ..config import settings
from . import llm
from .prompts import FOLLOWUP_SYSTEM, REVIEW_SYSTEM


class AlertReview(BaseModel):
    headline: str = Field(description="One sentence: what changed and why it matters")
    summary_bullets: list[str] = Field(description="3-5 bullets with exact values and dates")
    suggested_actions: list[str] = Field(description="2-4 concrete follow-up actions consistent with protocol")
    rationale: str = Field(description="Why these actions, citing [P#] protocol ids")


def _trend_line(points: list[dict], n: int = 5) -> str:
    return ", ".join(f"{p['date'][:10]}: {p['value']}" for p in points[-n:]) or "no data"


async def review_alert(patient_id: str, hits: list[dict]) -> dict:
    data = await clinical.patient_360(patient_id)
    prof, s = data["profile"], data["series"]
    protocol = await rag.search(" ".join(h["title"] for h in hits) + " escalation follow-up", ["clinician"], k=4)
    excerpts = "\n\n".join(f"[P{i + 1}] {r['title']} - {r['section']}: {r['content']}" for i, r in enumerate(protocol))
    context = (
        f"Patient: {prof['name']}, {prof['age']}y {prof['gender']}. Conditions: {', '.join(prof['conditions'])}. "
        f"Medications: {', '.join(prof['medications'])}.\n"
        f"Rule hits: {json.dumps(hits)}\n"
        f"ALT: {_trend_line(s['ALT'])}\nAST: {_trend_line(s['AST'])}\nPlatelets: {_trend_line(s['PLT'])}\n"
        f"FIB-4: {_trend_line(s['FIB4'])}\nHbA1c: {_trend_line(s['HBA1C'], 3)}\n"
        f"Weight (kg, recent): {_trend_line(s['WEIGHT'], 6)}\nSteps/day (recent): {_trend_line(s['STEPS'], 6)}\n"
        f"Care plan: {'; '.join(data['care_plan']['activities'])}\n\nProtocol excerpts:\n{excerpts}"
    )
    sources = [{"id": f"P{i + 1}", "title": r["title"], "section": r["section"], "version": r["version"]} for i, r in enumerate(protocol)]

    if llm.available():
        try:
            resp = await llm.client().messages.parse(
                model=settings.model_main,
                max_tokens=16000,
                system=REVIEW_SYSTEM,
                output_config={"effort": "medium"},
                messages=[{"role": "user", "content": context}],
                output_format=AlertReview,
            )
            if resp.parsed_output:
                return {**resp.parsed_output.model_dump(), "sources": sources, "generated_by": settings.model_main}
        except anthropic.APIError:
            pass
    # Deterministic fallback keeps the demo working without the LLM.
    return {
        "headline": f"{hits[0]['title']} for {prof['name']}.",
        "summary_bullets": [h["title"] if h["metric"] == "SYMPTOM" else f"{h['title']}: value {h['value']}" for h in hits]
        + [f"ALT trend: {_trend_line(s['ALT'], 3)}", f"Weight trend: {_trend_line(s['WEIGHT'], 3)}"],
        "suggested_actions": list(dict.fromkeys(h["suggested_action"] for h in hits)),
        "rationale": "Per rule catalog suggested actions [P1].",
        "sources": sources,
        "generated_by": "rules-template",
    }


async def compose_followup(patient_first_name: str, actions: list[str], clinician: str) -> str:
    if llm.available():
        try:
            resp = await llm.client().messages.create(
                model=settings.model_fast,
                max_tokens=2048,
                system=FOLLOWUP_SYSTEM,
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": f"Patient first name: {patient_first_name}\nApproved by: {clinician}\nApproved actions:\n- " + "\n- ".join(actions)}],
            )
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            if text:
                return text
        except anthropic.APIError:
            pass
    return (f"Hi {patient_first_name}, {clinician} reviewed your latest results and recommends: "
            + "; ".join(actions) + ". We'll be in touch to arrange this. Your LiverWell care team")
