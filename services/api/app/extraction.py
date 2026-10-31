"""Document AI: Claude reads an uploaded lab report (PDF or image) into a validated structure."""
import base64
from typing import Literal

from pydantic import BaseModel, Field

from .agents import llm
from .config import settings

TestKey = Literal["ALT", "AST", "PLT", "GGT", "HBA1C", "ALB", "OTHER"]

# Plausibility ranges (canonical units) - values outside are flagged for review, not saved silently.
PLAUSIBLE = {"ALT": (3, 2000), "AST": (3, 2000), "PLT": (10, 1000), "GGT": (3, 3000), "HBA1C": (3, 20), "ALB": (1, 7)}


class ExtractedResult(BaseModel):
    test_name: str = Field(description="Test name exactly as printed")
    key: TestKey = Field(description="Canonical key; OTHER if not one of the listed tests")
    value: float
    unit: str
    reference_range: str | None = None


class LabReport(BaseModel):
    patient_name: str | None
    collection_date: str | None = Field(description="ISO date YYYY-MM-DD the sample was collected")
    lab_name: str | None
    results: list[ExtractedResult]


PROMPT = """Extract the laboratory results from this report. Map each test to a canonical key:
ALT (alanine aminotransferase / SGPT), AST (aspartate aminotransferase / SGOT), PLT (platelet count, in 10^3/uL),
GGT (gamma-glutamyl transferase), HBA1C (hemoglobin A1c, %), ALB (albumin, g/dL); anything else is OTHER.
Copy values exactly as printed. Do not guess missing values."""


def _validate(report: LabReport, expected_name: str) -> dict:
    warnings = []
    if report.patient_name and expected_name.split()[-1].lower() not in report.patient_name.lower():
        warnings.append(f"Name on report ('{report.patient_name}') does not match the signed-in patient.")
    rows = []
    for r in report.results:
        status = "ok"
        if r.key == "OTHER":
            status = "not_tracked"
        else:
            value = r.value
            if r.key == "PLT" and value > 1000:  # reported per uL
                value = value / 1000
            lo, hi = PLAUSIBLE[r.key]
            if not lo <= value <= hi:
                status = "out_of_range"
                warnings.append(f"{r.test_name} value {r.value} {r.unit} is outside the plausible range.")
            r.value = value
        rows.append({**r.model_dump(), "status": status})
    if not report.collection_date:
        warnings.append("Collection date not found on the report.")
    return {"patient_name": report.patient_name, "collection_date": report.collection_date,
            "lab_name": report.lab_name, "results": rows, "warnings": warnings}


async def extract(data: bytes, media_type: str, expected_name: str) -> dict:
    if not llm.available():
        raise RuntimeError("Document extraction needs the Claude API key to be configured.")
    b64 = base64.standard_b64encode(data).decode()
    block = (
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
        if media_type == "application/pdf"
        else {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}
    )
    resp = await llm.client().messages.parse(
        model=settings.model_main,
        max_tokens=16000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": [block, {"type": "text", "text": PROMPT}]}],
        output_format=LabReport,
    )
    if not resp.parsed_output:
        raise RuntimeError("Could not read this document.")
    return _validate(resp.parsed_output, expected_name)
