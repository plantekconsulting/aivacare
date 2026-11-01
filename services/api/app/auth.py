"""Demo authentication: one-click personas issuing signed JWTs. Identity flows to MCP tools from here."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Query, Request

from .config import settings
from .seed.generate import PERSONAS


@dataclass
class User:
    sub: str
    role: str
    name: str


def can_approve(user: "User") -> bool:
    """Physicians sign off clinical decisions; coordinators triage and prepare."""
    return any(p["sub"] == user.sub and p.get("can_approve") for p in PERSONAS.values())


def issue_token(persona: str) -> str:
    p = PERSONAS[persona]
    payload = {"sub": p["sub"], "role": p["role"], "name": p["name"],
               "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode(token: str) -> User:
    try:
        p = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired session")
    return User(p["sub"], p["role"], p["name"])


def current_user(request: Request, token: str | None = Query(None)) -> User:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return _decode(header[7:])
    if token:  # EventSource cannot set headers
        return _decode(token)
    raise HTTPException(401, "Not signed in")


def require(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Not permitted for this role")
        return user
    return dep
