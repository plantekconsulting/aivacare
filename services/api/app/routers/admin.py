"""Presenter controls for the roadshow demo."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import fhir
from ..agents import llm
from ..auth import require
from ..config import settings
from ..seed import loader

router = APIRouter(prefix="/admin", dependencies=[Depends(require("admin"))])


@router.post("/reset")
async def reset() -> dict:
    return await loader.reset()


@router.post("/inject-labs")
async def inject() -> dict:
    return {"hits": await loader.inject_deterioration()}


class Advance(BaseModel):
    days: int = Field(7, ge=1, le=30)


@router.post("/advance-days")
async def advance(body: Advance) -> dict:
    return {"hits": await loader.advance_days(body.days)}


@router.get("/status")
async def status() -> dict:
    return {"fhir": await fhir.ready(), "llm_configured": llm.available(),
            "model_main": settings.model_main, "model_fast": settings.model_fast}
