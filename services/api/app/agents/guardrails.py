"""Input guardrails: deterministic red-flag bypass, then a fast-model scope / injection classifier."""
from typing import Literal

import anthropic
from pydantic import BaseModel

from ..config import settings
from ..rules.engine import detect_red_flags
from . import llm
from .prompts import GUARD_SYSTEM


class GuardVerdict(BaseModel):
    category: Literal["in_scope", "out_of_scope", "injection"]


RED_FLAG_RESPONSE = (
    "**This could be serious - please don't wait.**\n\n"
    "- If you are vomiting blood, have black or tarry stools, feel confused or very drowsy, or have severe abdominal pain, "
    "**call 911 or go to the nearest emergency department now.**\n"
    "- For yellowing of your skin or eyes or new belly swelling, **call LiverWell Clinic today**.\n\n"
    "I've alerted your care team so they can follow up with you."
)
OUT_OF_SCOPE_RESPONSE = "I can only help with your liver health, care plan and LiverWell services. Is there something about your health I can help with?"
INJECTION_RESPONSE = "I can't do that. I can help with questions about your own health, results and care plan."


async def check(text: str) -> tuple[str, list[str]]:
    """Returns (verdict, red_flags). verdict in red_flag | in_scope | out_of_scope | injection."""
    flags = detect_red_flags(text)
    if flags:
        return "red_flag", flags
    if not llm.available():
        return "in_scope", []
    try:
        resp = await llm.client().messages.parse(
            model=settings.model_fast,
            max_tokens=2048,
            system=GUARD_SYSTEM,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": f"<message>\n{text[:2000]}\n</message>"}],
            output_format=GuardVerdict,
        )
        return (resp.parsed_output.category if resp.parsed_output else "in_scope"), []
    except anthropic.APIError:
        return "in_scope", []  # fail open on classifier outage; red flags are already deterministic
