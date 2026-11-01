"""Synthetic demo data: John Miller's 12-month MASLD storyline + a background patient panel.

All data is synthetic. IDs are client-assigned so personas map to stable FHIR ids.
"""
import random
from datetime import date, datetime, time, timedelta, timezone

from .. import fhir
from ..rules.engine import fib4

PRACTITIONER_ID = "dr-anika-patel"
JOHN = "john-miller"

CONDITIONS = {
    "masld": ("197315008", "Non-alcoholic fatty liver disease (MASLD)"),
    "t2d": ("44054006", "Type 2 diabetes mellitus"),
    "obesity": ("414916001", "Obesity"),
    "hld": ("55822004", "Hyperlipidemia"),
    "htn": ("38341003", "Hypertension"),
}
MEDS = {
    "metformin": ("860975", "Metformin 500 mg tablet, twice daily"),
    "atorvastatin": ("617312", "Atorvastatin 20 mg tablet, daily"),
    "resmetirom": ("2678621", "Resmetirom 80 mg tablet, daily"),
    "semaglutide": ("1991302", "Semaglutide 1 mg weekly injection"),
    "lisinopril": ("314076", "Lisinopril 10 mg tablet, daily"),
}

# (id, given, family, gender, age, conditions, meds, lab series [months_ago -> (ALT, AST, PLT, GGT, HBA1C)], weight, steps, rhr)
PANEL = [
    ("maria-alvarez", "Maria", "Alvarez", "female", 56, ["masld", "t2d", "obesity"], ["metformin", "resmetirom"],
     [(78, 70, 160, 88, 7.9), (84, 76, 150, 92, 8.1), (90, 82, 142, 96, 8.0), (98, 90, 138, 101, 8.2)], 96, 4200, 74),
    ("david-thompson", "David", "Thompson", "male", 61, ["masld", "htn", "hld"], ["atorvastatin", "lisinopril"],
     [(48, 40, 210, 52, 5.9), (45, 38, 215, 50, 5.8), (44, 39, 212, 49, 5.8), (41, 36, 220, 47, 5.7)], 88, 7600, 66),
    ("aisha-rahman", "Aisha", "Rahman", "female", 42, ["masld", "obesity"], ["semaglutide"],
     [(66, 44, 260, 60, 6.1), (58, 40, 255, 55, 6.0), (49, 35, 262, 48, 5.9), (40, 30, 258, 41, 5.8)], 91, 8800, 68),
    ("kevin-obrien", "Kevin", "O'Brien", "male", 53, ["masld", "t2d", "hld"], ["metformin", "atorvastatin"],
     [(70, 52, 190, 75, 7.2), (74, 55, 185, 80, 7.4), (79, 60, 180, 84, 7.5), (88, 66, 176, 90, 7.6)], 109, 5100, 77),
    ("linda-park", "Linda", "Park", "female", 59, ["masld", "htn"], ["lisinopril"],
     [(39, 33, 230, 40, 5.6), (37, 31, 228, 38, 5.6), (36, 30, 232, 37, 5.5), (35, 30, 235, 36, 5.5)], 72, 9400, 64),
    ("marcus-johnson", "Marcus", "Johnson", "male", 45, ["masld", "obesity", "t2d"], ["metformin", "semaglutide"],
     [(92, 60, 240, 110, 8.4), (85, 55, 238, 104, 8.0), (80, 52, 241, 98, 7.7), (76, 50, 236, 95, 7.5)], 118, 3900, 79),
    ("priya-nair", "Priya", "Nair", "female", 50, ["masld", "hld"], ["atorvastatin"],
     [(55, 42, 200, 58, 5.9), (57, 44, 198, 60, 6.0), (60, 47, 196, 63, 6.0), (63, 52, 190, 66, 6.1)], 79, 6800, 70),
    ("thomas-weber", "Thomas", "Weber", "male", 64, ["masld", "t2d", "htn"], ["metformin", "lisinopril", "resmetirom"],
     [(62, 64, 150, 70, 7.0), (66, 70, 144, 74, 7.1), (64, 72, 140, 72, 7.2), (68, 78, 135, 77, 7.3)], 101, 4600, 75),
]

# John Miller: improving for 6 months on the lifestyle plan, then slipping as engagement dropped.
JOHN_LABS = [  # (days_ago, ALT, AST, PLT, GGT, HBA1C, ALB)
    (365, 82, 56, 228, 88, 6.9, 4.2),
    (275, 61, 44, 232, 70, 6.6, 4.3),
    (185, 44, 34, 235, 56, 6.3, 4.3),
    (95, 52, 36, 233, 61, 6.4, 4.2),
    (12, 67, 38, 230, 68, 6.6, 4.2),
]
# Injected by the presenter during the demo -> FIB-4 2.87 (high) and ALT doubled from baseline.
JOHN_DETERIORATION = {"ALT": 96, "AST": 88, "PLT": 150, "GGT": 95, "HBA1C": 6.8, "ALB": 4.0}


def _iso(d: date, hour: int = 9) -> str:
    return datetime.combine(d, time(hour, 0), tzinfo=timezone.utc).isoformat()


def _put(resource: dict) -> dict:
    return {"resource": resource, "request": {"method": "PUT", "url": f"{resource['resourceType']}/{resource['id']}"}}


def _post(resource: dict) -> dict:
    return {"resource": resource, "request": {"method": "POST", "url": resource["resourceType"]}}


def _patient(pid: str, given: str, family: str, gender: str, age: int, mrn: str) -> dict:
    birth = date.today().replace(year=date.today().year - age) - timedelta(days=40)
    return {
        "resourceType": "Patient", "id": pid,
        "identifier": [{"system": "https://liverwell.example/mrn", "value": mrn}],
        "name": [{"given": [given], "family": family}],
        "gender": gender, "birthDate": birth.isoformat(),
        "generalPractitioner": [{"reference": f"Practitioner/{PRACTITIONER_ID}"}],
    }


def _condition(pid: str, key: str, idx: int) -> dict:
    code, display = CONDITIONS[key]
    return {
        "resourceType": "Condition", "id": f"{pid}-cond-{idx}",
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": code, "display": display}], "text": display},
        "subject": {"reference": f"Patient/{pid}"},
    }


def _med(pid: str, key: str, idx: int) -> dict:
    code, display = MEDS[key]
    return {
        "resourceType": "MedicationStatement", "id": f"{pid}-med-{idx}", "status": "active",
        "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": code, "display": display}], "text": display},
        "subject": {"reference": f"Patient/{pid}"},
    }


def care_plan(pid: str, weight: float, activities: list[str] | None = None, version: int = 1) -> dict:
    target = round(weight * 0.92)
    acts = activities or [
        f"Weight goal: reach {target} kg (7-10% loss) over 12 months",
        "Mediterranean-style diet; limit added sugar and ultra-processed foods",
        "150+ minutes of moderate activity per week (target 8,000 steps/day)",
        "No alcohol",
        "Liver panel + FIB-4 every 3 months",
    ]
    return {
        "resourceType": "CarePlan", "id": f"{pid}-careplan", "status": "active", "intent": "plan",
        "title": "MASLD continuous care plan",
        "subject": {"reference": f"Patient/{pid}"},
        "author": {"reference": f"Practitioner/{PRACTITIONER_ID}"},
        "note": [{"text": f"version {version}"}],
        "activity": [{"detail": {"status": "in-progress", "description": a}} for a in acts],
    }


def _labs(pid: str, age: int, when: str, alt, ast, plt, ggt, a1c, alb=None) -> list[dict]:
    vals = {"ALT": alt, "AST": ast, "PLT": plt, "GGT": ggt, "HBA1C": a1c}
    if alb:
        vals["ALB"] = alb
    obs = [fhir.observation(pid, k, v, when) for k, v in vals.items()]
    obs.append(fhir.observation(pid, "FIB4", fib4(age, ast, alt, plt), when, source="rules-engine"))
    return obs


def wearable_day(pid: str, d: date, weight: float, steps: float, rhr: float, sleep: float, rng: random.Random) -> list[dict]:
    when = _iso(d, 7)
    return [
        fhir.observation(pid, "WEIGHT", weight + rng.uniform(-0.3, 0.3), when, source="apple-watch"),
        fhir.observation(pid, "STEPS", max(800, steps + rng.uniform(-1200, 1200)), when, source="apple-watch"),
        fhir.observation(pid, "RHR", rhr + rng.uniform(-2, 2), when, source="apple-watch"),
        fhir.observation(pid, "SLEEP", max(4, sleep + rng.uniform(-0.6, 0.6)), when, source="apple-watch"),
    ]


def john_wearable_profile(days_ago: int) -> tuple[float, float, float, float]:
    """(weight, steps, rhr, sleep) for John on a given day - improves, then slips over the last ~100 days."""
    if days_ago > 180:
        f = (365 - days_ago) / 185  # 0 -> 1
        return 104 - 6 * f, 5200 + 3800 * f, 76 - 6 * f, 6.2 + 0.8 * f
    if days_ago > 100:
        return 98.0, 9000, 70, 7.0
    f = (100 - days_ago) / 100  # 0 -> 1 slipping
    return 98 + 2.4 * f, 9000 - 3400 * f, 70 + 4 * f, 7.0 - 0.7 * f


def build_bundles() -> list[list[dict]]:
    rng = random.Random(42)
    today = date.today()
    bundles: list[list[dict]] = []

    practitioner = {
        "resourceType": "Practitioner", "id": PRACTITIONER_ID,
        "name": [{"prefix": ["Dr."], "given": ["Anika"], "family": "Patel"}],
        "qualification": [{"code": {"text": "Hepatologist"}}],
    }
    org = {"resourceType": "Organization", "id": "liverwell", "name": "LiverWell Clinic"}

    # John Miller
    entries = [_put(org), _put(practitioner), _put(_patient(JOHN, "John", "Miller", "male", 48, "LW-100482"))]
    entries += [_put(_condition(JOHN, k, i)) for i, k in enumerate(["masld", "t2d", "obesity", "hld"])]
    entries += [_put(_med(JOHN, k, i)) for i, k in enumerate(["metformin", "atorvastatin"])]
    entries.append(_put(care_plan(JOHN, 104)))
    for days_ago, alt, ast, plt, ggt, a1c, alb in JOHN_LABS:
        entries += [_post(o) for o in _labs(JOHN, 48, _iso(today - timedelta(days=days_ago), 8), alt, ast, plt, ggt, a1c, alb)]
    for days_ago in range(365, 0, -1):
        if days_ago > 120 and days_ago % 7:
            continue  # weekly before the last 120 days, daily after
        w, s, r, sl = john_wearable_profile(days_ago)
        entries += [_post(o) for o in wearable_day(JOHN, today - timedelta(days=days_ago), w, s, r, sl, rng)]
    bundles.append(entries)

    for i, (pid, given, family, gender, age, conds, meds, labs, weight, steps, rhr) in enumerate(PANEL):
        e = [_put(_patient(pid, given, family, gender, age, f"LW-1005{i:02d}"))]
        e += [_put(_condition(pid, k, j)) for j, k in enumerate(conds)]
        e += [_put(_med(pid, k, j)) for j, k in enumerate(meds)]
        e.append(_put(care_plan(pid, weight)))
        for j, (alt, ast, plt, ggt, a1c) in enumerate(labs):
            e += [_post(o) for o in _labs(pid, age, _iso(today - timedelta(days=270 - j * 90 + rng.randint(0, 6)), 8), alt, ast, plt, ggt, a1c)]
        for days_ago in range(120, 0, -7):
            e += [_post(o) for o in wearable_day(pid, today - timedelta(days=days_ago), weight, steps, rhr, 6.8, rng)]
        bundles.append(e)
    return bundles


PERSONAS = {
    "john": {"sub": JOHN, "role": "patient", "name": "John Miller", "title": "Patient, 48"},
    "dr-patel": {"sub": PRACTITIONER_ID, "role": "clinician", "name": "Dr. Anika Patel", "title": "Hepatologist", "can_approve": True},
    "coordinator": {"sub": "coord-sam-lee", "role": "clinician", "name": "Sam Lee, RN", "title": "Care Coordinator"},
    "admin": {"sub": "admin", "role": "admin", "name": "Demo Admin", "title": "Presenter controls"},
}
