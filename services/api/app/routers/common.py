"""Auth, personas and the live event stream."""
import asyncio
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import events
from ..auth import User, current_user, issue_token
from ..config import settings
from ..seed.generate import PERSONAS

router = APIRouter()


@router.get("/personas")
async def personas() -> list[dict]:
    return [{"key": k, **{f: p[f] for f in ("name", "title", "role")}} for k, p in PERSONAS.items()]


@router.post("/login/{persona}")
async def login(persona: str, code: str = "") -> dict:
    """Team access gate: when DEMO_ACCESS_CODE is set, sign-in requires it."""
    if settings.access_code and not hmac.compare_digest(code, settings.access_code):
        raise HTTPException(403, "Invalid access code")
    if persona not in PERSONAS:
        raise HTTPException(404, "Unknown persona")
    p = PERSONAS[persona]
    return {"token": issue_token(persona), "role": p["role"], "name": p["name"], "sub": p["sub"]}


@router.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return user.__dict__


@router.get("/events")
async def stream(request: Request, user: User = Depends(current_user)):
    sub = events.subscribe(user.role, user.sub)

    async def gen():
        try:
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                try:
                    msg = await asyncio.wait_for(sub.queue.get(), timeout=15)
                    yield f"data: {msg}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            events.unsubscribe(sub)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
