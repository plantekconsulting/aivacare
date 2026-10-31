from datetime import date, timedelta

import pytest

from app.rules.engine import detect_red_flags, evaluate, fib4
from app.seed.generate import JOHN_DETERIORATION, JOHN_LABS


def pts(values, start_days_ago=400, step=90):
    d0 = date.today() - timedelta(days=start_days_ago)
    return [{"date": (d0 + timedelta(days=i * step)).isoformat() + "T08:00:00+00:00", "value": v} for i, v in enumerate(values)]


def test_fib4_formula():
    # 48y, AST 88, ALT 96, PLT 150 -> 2.87
    assert fib4(48, 88, 96, 150) == 2.87
    with pytest.raises(ValueError):
        fib4(48, 30, 0, 200)


def test_john_seed_is_clean_and_deterioration_triggers_high():
    *_, last = JOHN_LABS
    _, alt, ast, plt, *_ = last
    assert fib4(48, ast, alt, plt) < 1.3
    d = JOHN_DETERIORATION
    assert fib4(48, d["AST"], d["ALT"], d["PLT"]) > 2.67


def test_fib4_bands_most_severe_wins():
    hits = evaluate({"FIB4": pts([0.9, 2.9])})
    assert [h.rule_id for h in hits] == ["fib4_high"]
    hits = evaluate({"FIB4": pts([0.9, 1.8])})
    assert [h.rule_id for h in hits] == ["fib4_indeterminate"]
    assert evaluate({"FIB4": pts([0.9, 1.1])}) == []


def test_alt_doubled_from_baseline():
    hits = evaluate({"ALT": pts([82, 61, 44, 52, 96])})
    assert hits[0].rule_id == "alt_doubled_from_baseline"
    assert hits[0].evidence["baseline"] == 44


def test_alt_above_3x_uln_is_high():
    hits = evaluate({"ALT": pts([40, 130])})
    assert hits[0].rule_id == "alt_above_3x_uln" and hits[0].priority == "high"


def test_weight_gain_30d():
    daily = pts([100 + i * 0.15 for i in range(40)], start_days_ago=40, step=1)
    hits = evaluate({"WEIGHT": daily})
    assert hits and hits[0].rule_id == "weight_gain_30d"


@pytest.mark.parametrize("text,expected", [
    ("my eyes look yellow today", ["jaundice"]),
    ("I vomited blood this morning", ["gi_bleed"]),
    ("I feel confused and dizzy", ["confusion"]),
    ("What should I eat for breakfast?", []),
])
def test_red_flags(text, expected):
    assert detect_red_flags(text) == expected
