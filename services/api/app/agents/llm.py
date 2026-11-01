"""Claude client + shared helpers."""
import os
from datetime import date

import anthropic

from ..config import settings

_client: anthropic.AsyncAnthropic | None = None

# Models that accept the server-side refusal fallback ("default" routing).
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}


_usage = {"day": "", "calls": 0}


def configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def usage() -> dict:
    today = date.today().isoformat()
    if _usage["day"] != today:
        _usage.update(day=today, calls=0)
    return {"calls_today": _usage["calls"], "daily_limit": settings.ai_daily_call_limit}


def available() -> bool:
    """Key present and today's call budget not spent; otherwise callers use their non-AI fallbacks."""
    u = usage()
    return configured() and u["calls_today"] < u["daily_limit"]


def client() -> anthropic.AsyncAnthropic:
    """Every Claude request goes through here, so each call is counted against the daily budget."""
    global _client
    usage()
    _usage["calls"] += 1
    if _client is None:
        _client = anthropic.AsyncAnthropic(max_retries=3)
    return _client


def fallback_kwargs(model: str) -> dict:
    """Server-side refusal fallback; the API re-routes a declined request instead of stopping."""
    if model in _FALLBACK_MODELS:
        return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    return {}
