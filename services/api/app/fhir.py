"""Thin async client for the HAPI FHIR R4 server (system of record)."""
from datetime import datetime, timezone

import httpx

from .config import settings

# key -> (LOINC code, display, unit)
LOINC = {
    "ALT": ("1742-6", "Alanine aminotransferase", "U/L"),
    "AST": ("1920-8", "Aspartate aminotransferase", "U/L"),
    "PLT": ("777-3", "Platelets", "10*3/uL"),
    "GGT": ("2324-2", "Gamma glutamyl transferase", "U/L"),
    "HBA1C": ("4548-4", "Hemoglobin A1c", "%"),
    "ALB": ("1751-7", "Albumin", "g/dL"),
    "WEIGHT": ("29463-7", "Body weight", "kg"),
    "STEPS": ("41950-7", "Steps in 24 hours", "steps"),
    "RHR": ("40443-4", "Resting heart rate", "/min"),
    "SLEEP": ("93832-4", "Sleep duration", "h"),
    "FIB4": ("fib-4", "FIB-4 index", "score"),
}
CODE_TO_KEY = {v[0]: k for k, v in LOINC.items()}
LAB_KEYS = {"ALT", "AST", "PLT", "GGT", "HBA1C", "ALB"}
WEARABLE_KEYS = {"STEPS", "RHR", "SLEEP", "WEIGHT"}
SOURCE_SYSTEM = "https://aivacare.dev/source"

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.fhir_base_url,
            timeout=120.0,
            headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
        )
    return _client


async def ready() -> bool:
    try:
        r = await client().get("/metadata", params={"_summary": "true"})
        return r.status_code == 200
    except httpx.HTTPError:
        return False


async def search(resource: str, params: dict) -> list[dict]:
    """Search and follow paging; returns resources."""
    out: list[dict] = []
    r = await client().get(f"/{resource}", params=params)
    r.raise_for_status()
    bundle = r.json()
    while True:
        out.extend(e["resource"] for e in bundle.get("entry", []))
        nxt = next((l["url"] for l in bundle.get("link", []) if l["relation"] == "next"), None)
        if not nxt:
            return out
        r = await client().get(nxt)
        r.raise_for_status()
        bundle = r.json()


async def read(resource: str, rid: str) -> dict:
    r = await client().get(f"/{resource}/{rid}")
    r.raise_for_status()
    return r.json()


async def create(resource: dict) -> dict:
    r = await client().post(f"/{resource['resourceType']}", json=resource)
    r.raise_for_status()
    return r.json()


async def update(resource: dict) -> dict:
    r = await client().put(f"/{resource['resourceType']}/{resource['id']}", json=resource)
    r.raise_for_status()
    return r.json()


async def transaction(entries: list[dict]) -> dict:
    bundle = {"resourceType": "Bundle", "type": "transaction", "entry": entries}
    r = await client().post("", json=bundle)
    r.raise_for_status()
    return r.json()


async def expunge_everything() -> None:
    r = await client().post(
        "/$expunge",
        json={"resourceType": "Parameters", "parameter": [{"name": "expungeEverything", "valueBoolean": True}]},
    )
    r.raise_for_status()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def observation(patient_id: str, key: str, value: float, when: str, source: str = "ehr") -> dict:
    code, display, unit = LOINC[key]
    if key in LAB_KEYS or key == "FIB4":
        category = "laboratory"
    elif key in {"WEIGHT", "RHR"}:
        category = "vital-signs"
    else:
        category = "activity"
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": category}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}], "text": display},
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": when,
        "valueQuantity": {"value": round(value, 2), "unit": unit},
        "meta": {"tag": [{"system": SOURCE_SYSTEM, "code": source}]},
    }


async def observations(patient_id: str, key: str, since: str | None = None) -> list[dict]:
    """Returns [{'date', 'value', 'source'}] sorted by date ascending."""
    params = {"subject": f"Patient/{patient_id}", "code": LOINC[key][0], "_sort": "date", "_count": "500"}
    if since:
        params["date"] = f"ge{since}"
    pts = []
    for o in await search("Observation", params):
        tags = o.get("meta", {}).get("tag", [])
        pts.append({
            "date": o["effectiveDateTime"],
            "value": o["valueQuantity"]["value"],
            "source": next((t["code"] for t in tags if t.get("system") == SOURCE_SYSTEM), "ehr"),
        })
    return pts
