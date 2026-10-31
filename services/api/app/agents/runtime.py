"""Agent loop: Claude + MCP tools, streamed as UI events.

Yields dicts: {"type": "text", "delta"} | {"type": "tool", "name", "label", "status"} | {"type": "error", "message"}
"""
import json
from collections.abc import AsyncIterator

import anthropic
from fastmcp import Client, FastMCP

from ..config import settings
from . import llm

MAX_STEPS = 8

TOOL_LABELS = {
    "get_my_trend": "Checked your trend data",
    "get_my_latest_results": "Looked up your latest results",
    "get_my_profile": "Reviewed your profile",
    "get_my_care_plan": "Reviewed your care plan",
    "get_my_progress": "Checked your progress",
    "search_guidance": "Searched approved guidance",
    "log_symptom": "Logged your symptom",
    "request_appointment": "Sent an appointment request",
    "list_my_documents": "Checked your documents",
    "list_patient_panel": "Listed patient panel",
    "get_patient_summary": "Pulled Patient 360",
    "get_trend": "Pulled trend",
    "get_risk_flags": "Ran rules engine",
    "list_open_alerts": "Listed open alerts",
    "propose_careplan_change": "Drafted care-plan proposal",
    "list_patient_documents": "Checked documents",
}


def _label(tool_name: str) -> str:
    base = tool_name.split("_", 1)[1] if "_" in tool_name else tool_name
    return TOOL_LABELS.get(base, base.replace("_", " "))


async def run_agent(system: str, history: list[dict], gateway: FastMCP, effort: str = "low") -> AsyncIterator[dict]:
    model = settings.model_main
    if not llm.available():
        yield {"type": "error", "message": "The AI assistant isn't configured yet (missing Claude API key)."}
        return
    async with Client(gateway) as mcp:
        tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.input_schema, "eager_input_streaming": True}
            for t in await mcp.list_tools()
        ]
        messages = list(history)
        for _ in range(MAX_STEPS):
            try:
                async with llm.client().beta.messages.stream(
                    model=model,
                    max_tokens=16000,
                    system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                    tools=tools,
                    messages=messages,
                    output_config={"effort": effort},
                    **llm.fallback_kwargs(model),
                ) as stream:
                    async for event in stream:
                        if event.type == "text":
                            yield {"type": "text", "delta": event.text}
                    response = await stream.get_final_message()
            except ValueError:
                continue  # unparseable streamed tool JSON - re-issue the turn
            except anthropic.APIError as e:
                yield {"type": "error", "message": f"The assistant is temporarily unavailable ({type(e).__name__})."}
                return

            if response.stop_reason == "refusal":
                yield {"type": "text", "delta": "\n\nI'm not able to help with that here. Please contact your care team."}
                return
            messages.append({"role": "assistant", "content": response.content})
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason == "pause_turn":
                continue
            if not tool_uses or response.stop_reason == "max_tokens":
                return

            results = []
            for block in tool_uses:
                label = _label(block.name)
                yield {"type": "tool", "name": block.name, "label": label, "status": "running"}
                if not isinstance(block.input, dict):
                    results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                                    "content": json.dumps({"INVALID_JSON": str(block.input)})})
                    continue
                result = await mcp.call_tool(block.name, block.input, raise_on_error=False)
                text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text") or "(no content)"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": bool(result.is_error)})
                yield {"type": "tool", "name": block.name, "label": label, "status": "error" if result.is_error else "done"}
            messages.append({"role": "user", "content": results})
        yield {"type": "text", "delta": "\n\n(I've reached my step limit for this question.)"}
