"""Auth, personas and the live event stream."""
import asyncio
import hmac
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import events
from ..auth import User, can_approve, current_user, issue_token
from ..config import settings
from ..seed.generate import PERSONAS

router = APIRouter()
_login_failures: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Caddy replaces any client-sent X-Forwarded-For with the real peer address, so the last entry is trustworthy.
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "unknown")


@router.get("/personas")
async def personas() -> list[dict]:
    return [{"key": k, **{f: p[f] for f in ("name", "title", "role")}} for k, p in PERSONAS.items()]


@router.post("/login/{persona}")
async def login(persona: str, request: Request, code: str = "") -> dict:
    """Team access gate: when DEMO_ACCESS_CODE is set, sign-in requires it.
    Wrong codes are counted per client IP; too many and that IP is locked out for 15 minutes."""
    if settings.access_code:
        ip = _client_ip(request)
        failures = _login_failures[ip]
        now = time.monotonic()
        while failures and now - failures[0] > 900:
            failures.popleft()
        if len(failures) >= settings.login_failures_per_15min:
            raise HTTPException(429, "Too many attempts - try again in 15 minutes.")
        if not hmac.compare_digest(code, settings.access_code):
            failures.append(now)
            raise HTTPException(403, "Invalid access code")
    if persona not in PERSONAS:
        raise HTTPException(404, "Unknown persona")
    p = PERSONAS[persona]
    return {"token": issue_token(persona), "role": p["role"], "name": p["name"], "sub": p["sub"], "can_approve": bool(p.get("can_approve"))}


@router.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {**user.__dict__, "can_approve": can_approve(user)}


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
