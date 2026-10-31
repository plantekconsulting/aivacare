import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db, fhir, rag
from .config import settings
from .routers import admin, clinician, common, patient
from .workflows import escalation

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("aivacare")


async def _wait_for_fhir(timeout_s: int = 300) -> None:
    for _ in range(timeout_s // 5):
        if await fhir.ready():
            return
        log.info("waiting for FHIR server...")
        await asyncio.sleep(5)
    raise RuntimeError("FHIR server not reachable")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await escalation.init()
    await _wait_for_fhir()
    if not (await db.fetch("SELECT count(*) AS n FROM kb_chunks"))[0]["n"]:
        log.info("ingested %d knowledge chunks", await rag.ingest())
    if not await fhir.search("Patient", {"_id": "john-miller"}):
        from .seed import loader

        log.info("seeding demo data: %s", await loader.reset())
    yield
    await db.close_db()


app = FastAPI(title="AivaCare API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["x-vercel-ai-ui-message-stream"])
for r in (common.router, patient.router, clinician.router, admin.router):
    app.include_router(r)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}
