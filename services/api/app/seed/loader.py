"""Demo reset + seeding + simulator actions used by the admin panel."""
import random
from datetime import date, datetime, time, timedelta, timezone

from .. import clinical, db, fhir, rag
from ..workflows import escalation
from . import generate


async def reset() -> dict:
    await fhir.expunge_everything()
    for table in ("notifications", "uploads", "audit_log"):
        await db.execute(f"TRUNCATE {table}")
    for entries in generate.build_bundles():
        await fhir.transaction(entries)
    if not (await db.fetch("SELECT count(*) AS n FROM kb_chunks"))[0]["n"]:
        await rag.ingest()

    await clinical.notify(generate.JOHN, "reminder", "Lab draw due soon",
                          "Your quarterly liver panel is due in the next 2 weeks. Book at any partner lab.")
    await clinical.notify(generate.JOHN, "reminder", "Weekly check-in", "Log how you're feeling and keep your watch on overnight to track sleep.")
    await db.audit("admin", "demo.reset", {})

    started = 0
    for pid, *_ in generate.PANEL:
        hits = await clinical.evaluate_rules(pid)
        if hits:
            escalation.start(pid, hits)
            started += 1
    return {"patients": 1 + len(generate.PANEL), "escalations_started": started}


async def inject_deterioration(pid: str = generate.JOHN) -> list[dict]:
    when = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    obs = [fhir.observation(pid, k, v, when, source="lab-feed") for k, v in generate.JOHN_DETERIORATION.items()]
    hits = await clinical.ingest_observations(pid, obs, actor="lab-feed")
    if hits:
        escalation.start(pid, hits)
    return hits


async def advance_days(days: int, pid: str = generate.JOHN) -> list[dict]:
    """Wearable simulator: continue John's slipping trajectory for N more days."""
    pts = await fhir.observations(pid, "STEPS")
    last = date.fromisoformat(pts[-1]["date"][:10]) if pts else date.today() - timedelta(days=1)
    w = (await fhir.observations(pid, "WEIGHT"))[-1]["value"]
    rng = random.Random(last.toordinal())
    obs = []
    for i in range(1, days + 1):
        d = last + timedelta(days=i)
        obs += generate.wearable_day(pid, d, w + 0.12 * i, 4200 - 60 * i, 75 + 0.3 * i, 6.0, rng)
    hits = await clinical.ingest_observations(pid, obs, actor="apple-watch-sync")
    if hits:
        escalation.start(pid, hits)
    return hits
