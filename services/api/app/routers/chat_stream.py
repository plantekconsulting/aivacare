"""Adapts agent events to the Vercel AI SDK UI message stream protocol (SSE), consumed by useChat()."""
import json
import re
import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from ..config import settings

HEADERS = {"x-vercel-ai-ui-message-stream": "v1", "Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
_calls: dict[str, deque] = defaultdict(deque)


def limit(key: str, max_calls: int, window_s: int, message: str) -> None:
    """Sliding-window limiter (in-process; fine for the single demo VM)."""
    now, q = time.monotonic(), _calls[key]
    while q and now - q[0] > window_s:
        q.popleft()
    if len(q) >= max_calls:
        raise HTTPException(429, message)
    q.append(now)


def rate_limit(sub: str) -> None:
    limit(f"chat:{sub}", settings.chat_rate_per_minute, 60, "Too many messages - please wait a moment.")


def history_from_ui(messages: list[dict], max_turns: int = 12) -> list[dict]:
    """UIMessage[] -> Anthropic messages (text only). Must end with a user turn.
    The history comes from the client, so every turn is length-capped before it reaches Claude."""
    cap = settings.max_message_chars
    if messages:
        last = "".join(p.get("text", "") for p in messages[-1].get("parts", []) if p.get("type") == "text")
        if len(last) > cap:
            raise HTTPException(413, f"Please keep messages under {cap} characters.")
    out = []
    for m in messages[-max_turns:]:
        if m.get("role") not in ("user", "assistant"):
            continue
        text = "".join(p.get("text", "") for p in m.get("parts", []) if p.get("type") == "text").strip()
        if not text:
            continue
        text = text[: cap * 2]
        if out and out[-1]["role"] == m["role"]:
            out[-1]["content"] += "\n\n" + text
        else:
            out.append({"role": m["role"], "content": text})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _shown_sources(sources: list[dict], text: str) -> list[dict]:
    """Sources the answer cites ([S1]...); if it cites none, one per document."""
    cited = set(re.findall(r"\bS\d+\b", text))
    if picked := [s for s in sources if s["id"] in cited]:
        return picked
    seen: set[str] = set()
    return [s for s in sources if not (s["title"] in seen or seen.add(s["title"]))]


def ui_stream(events: AsyncIterator[dict], sources_fn=lambda: []) -> StreamingResponse:
    async def gen():
        text_id = f"t-{uuid.uuid4().hex[:8]}"
        full = ""
        yield _sse({"type": "start", "messageId": f"m-{uuid.uuid4().hex[:10]}"})
        yield _sse({"type": "text-start", "id": text_id})
        try:
            async for ev in events:
                if ev["type"] == "text":
                    full += ev["delta"]
                    yield _sse({"type": "text-delta", "id": text_id, "delta": ev["delta"]})
                elif ev["type"] == "tool":
                    yield _sse({"type": "data-tool", "id": f"{ev['name']}", "data": {"label": ev["label"], "status": ev["status"]}})
                elif ev["type"] == "error":
                    yield _sse({"type": "text-delta", "id": text_id, "delta": ev["message"]})
        finally:
            yield _sse({"type": "text-end", "id": text_id})
            for s in _shown_sources(sources_fn(), full):
                yield _sse({"type": "data-source", "id": s["id"], "data": s})
            yield _sse({"type": "finish", "finishReason": "stop"})
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers=HEADERS)


async def single_message(text: str) -> AsyncIterator[dict]:
    yield {"type": "text", "delta": text}
