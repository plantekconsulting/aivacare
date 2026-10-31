"""Patient-facing API (mobile app + web portal). Every route is scoped to the signed-in patient."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from psycopg.types.json import Jsonb

from .. import clinical, db, extraction, fhir
from ..agents import guardrails, runtime
from ..agents.prompts import PATIENT_SYSTEM
from ..auth import User, require
from ..mcp_servers import SourceRegistry, patient_gateway, symptom_hit
from ..workflows import escalation
from .chat_stream import history_from_ui, rate_limit, single_message, ui_stream

router = APIRouter(prefix="/patient")
Patient = Depends(require("patient"))
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}


@router.get("/home")
async def home(user: User = Patient) -> dict:
    data = await clinical.patient_360(user.sub)
    for k in fhir.WEARABLE_KEYS:  # keep payload small for mobile
        data["series"][k] = data["series"][k][-90:]
    return data


@router.get("/notifications")
async def notifications(user: User = Patient) -> list[dict]:
    return await clinical.notifications(user.sub)


@router.post("/notifications/read")
async def mark_read(user: User = Patient) -> dict:
    await db.execute("UPDATE notifications SET read = TRUE WHERE patient_id = %s", user.sub)
    return {"ok": True}


@router.post("/chat")
async def chat(body: dict, user: User = Patient):
    rate_limit(user.sub)
    history = history_from_ui(body.get("messages", []))
    if not history or history[-1]["role"] != "user":
        raise HTTPException(400, "No question received")
    question = history[-1]["content"]

    verdict, flags = await guardrails.check(question)
    await db.audit(user.sub, "chat.message", {"verdict": verdict, "red_flags": flags})
    if verdict == "red_flag":
        escalation.start(user.sub, [symptom_hit(question, "high")], source="red-flag-guardrail")
        return ui_stream(single_message(guardrails.RED_FLAG_RESPONSE))
    if verdict == "out_of_scope":
        return ui_stream(single_message(guardrails.OUT_OF_SCOPE_RESPONSE))
    if verdict == "injection":
        return ui_stream(single_message(guardrails.INJECTION_RESPONSE))

    registry = SourceRegistry()
    system = PATIENT_SYSTEM + f"\n\nToday is {date.today().isoformat()}. The patient is {user.name}."
    events = runtime.run_agent(system, history, patient_gateway(user, registry), effort="low")
    return ui_stream(events, lambda: registry.sources)


@router.post("/documents")
async def upload(file: UploadFile, user: User = Patient) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a PDF or a photo (PNG/JPEG).")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 15 MB).")
    rows = await db.fetch(
        "INSERT INTO uploads (patient_id, filename, media_type, data) VALUES (%s, %s, %s, %s) RETURNING id",
        user.sub, file.filename, file.content_type, data,
    )
    upload_id = rows[0]["id"]
    try:
        result = await extraction.extract(data, file.content_type, user.name)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    await db.execute("UPDATE uploads SET extraction = %s, status = 'extracted' WHERE id = %s", Jsonb(result), upload_id)
    await db.audit(user.sub, "document.extracted", {"upload_id": upload_id, "results": len(result["results"])})
    return {"upload_id": upload_id, **result}


@router.post("/documents/{upload_id}/confirm")
async def confirm(upload_id: int, user: User = Patient) -> dict:
    rows = await db.fetch("SELECT extraction, status FROM uploads WHERE id = %s AND patient_id = %s", upload_id, user.sub)
    if not rows or rows[0]["status"] != "extracted":
        raise HTTPException(404, "Nothing to confirm")
    ext = rows[0]["extraction"]
    when = (ext.get("collection_date") or date.today().isoformat())[:10] + "T08:00:00+00:00"
    obs = [fhir.observation(user.sub, r["key"], r["value"], when, source="patient-upload")
           for r in ext["results"] if r["status"] == "ok"]
    if not obs:
        raise HTTPException(422, "No trackable results to save")
    for o in obs:  # provenance: link each value back to the uploaded document
        o["derivedFrom"] = [{"display": f"Uploaded report #{upload_id}"}]
    hits = await clinical.ingest_observations(user.sub, obs, actor=user.sub)
    await db.execute("UPDATE uploads SET status = 'confirmed' WHERE id = %s", upload_id)
    if hits:
        escalation.start(user.sub, hits, source="patient-upload")
    return {"saved": len(obs), "new_alerts": len(hits)}
