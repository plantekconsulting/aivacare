"""Deterministic clinical rules engine. No LLM involvement: rules decide, AI explains."""
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

import yaml

CATALOG = yaml.safe_load((Path(__file__).parent / "rules.yaml").read_text(encoding="utf-8"))
RULES = {r["id"]: r for r in CATALOG["rules"]}
SLA_HOURS = CATALOG["sla_hours"]
PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}


@dataclass
class RuleHit:
    rule_id: str
    priority: str
    title: str
    suggested_action: str
    metric: str
    value: float
    threshold: float | list
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def fib4(age: float, ast: float, alt: float, platelets: float) -> float:
    """FIB-4 = (age x AST) / (platelets[10^9/L] x sqrt(ALT))."""
    if alt <= 0 or platelets <= 0:
        raise ValueError("ALT and platelets must be positive")
    return round((age * ast) / (platelets * math.sqrt(alt)), 2)


def _hit(rule: dict, value: float, **evidence) -> RuleHit:
    return RuleHit(
        rule_id=rule["id"], priority=rule["priority"], title=rule["title"],
        suggested_action=rule["suggested_action"], metric=rule["metric"],
        value=round(value, 2), threshold=rule["threshold"], evidence=evidence,
    )


def _parse(d: str) -> datetime:
    return datetime.fromisoformat(d.replace("Z", "+00:00"))


def evaluate(series: dict[str, list[dict]]) -> list[RuleHit]:
    """Evaluate all rules against time series {metric: [{'date', 'value'}] ascending}.

    Lab rules look at the latest value; wearable rules compare recent windows to baseline.
    Within a metric only the most severe hit is returned (e.g. FIB-4 high suppresses indeterminate).
    """
    hits: list[RuleHit] = []
    for rule in CATALOG["rules"]:
        pts = series.get(rule["metric"]) or []
        if not pts:
            continue
        latest = pts[-1]
        kind, thr = rule["kind"], rule["threshold"]
        if kind == "above" and latest["value"] > thr:
            hits.append(_hit(rule, latest["value"], date=latest["date"]))
        elif kind == "between" and thr[0] <= latest["value"] <= thr[1]:
            hits.append(_hit(rule, latest["value"], date=latest["date"]))
        elif kind == "ratio_to_baseline" and len(pts) >= 2:
            baseline = min(p["value"] for p in pts[:-1])
            if baseline > 0 and latest["value"] / baseline >= thr:
                hits.append(_hit(rule, latest["value"], baseline=baseline, date=latest["date"]))
        elif kind in {"pct_change_30d", "rise_vs_baseline", "drop_pct_vs_baseline"}:
            end = _parse(latest["date"])
            recent = [p["value"] for p in pts if _parse(p["date"]) > end - timedelta(days=7)]
            base = [p["value"] for p in pts if end - timedelta(days=60) < _parse(p["date"]) <= end - timedelta(days=14)]
            if kind == "pct_change_30d":
                prior = [p for p in pts if _parse(p["date"]) <= end - timedelta(days=30)]
                if prior:
                    change = (latest["value"] - prior[-1]["value"]) / prior[-1]["value"] * 100
                    if change > thr:
                        hits.append(_hit(rule, change, from_value=prior[-1]["value"], to_value=latest["value"]))
            elif recent and base:
                r, b = mean(recent), mean(base)
                if kind == "rise_vs_baseline" and r - b > thr:
                    hits.append(_hit(rule, r - b, recent_avg=round(r, 1), baseline_avg=round(b, 1)))
                if kind == "drop_pct_vs_baseline" and b > 0 and (b - r) / b * 100 > thr:
                    hits.append(_hit(rule, (b - r) / b * 100, recent_avg=round(r), baseline_avg=round(b)))

    best: dict[str, RuleHit] = {}
    for h in hits:
        if h.metric not in best or PRIORITY_RANK[h.priority] > PRIORITY_RANK[best[h.metric].priority]:
            best[h.metric] = h
    return sorted(best.values(), key=lambda h: -PRIORITY_RANK[h.priority])


_RED_FLAG_RES = [
    (rf["term"], re.compile("|".join(re.escape(p) for p in rf["patterns"]), re.IGNORECASE))
    for rf in CATALOG["red_flags"]
]


def detect_red_flags(text: str) -> list[str]:
    return [term for term, rx in _RED_FLAG_RES if rx.search(text)]
