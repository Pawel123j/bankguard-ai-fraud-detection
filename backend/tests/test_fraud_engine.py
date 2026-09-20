"""Tests for the fraud scoring engine.

This is the only piece of real decision logic in the service: it decides which
transactions an analyst sees first. Each signal, each boundary and each coercion
path is pinned down here, because a silent change to any of them changes the
queue without anything else failing.

The weights under test are the ones documented in the README scoring table —
the two must stay in step.
"""

from __future__ import annotations

import pytest

from app.fraud_engine import risk_level_for_score, score_transaction

# A transaction that trips no rule at all. Individual tests override one field
# at a time, so each assertion isolates a single signal.
BASELINE = {
    "amount": 50.0,
    "is_foreign": False,
    "is_night_transaction": False,
    "previous_failed_attempts": 0,
    "device_trust_score": 95,
    "merchant_category": "Groceries",
    "country": "United States",
}


def score(**overrides) -> dict:
    return score_transaction({**BASELINE, **overrides})


# --- individual signals and their documented weights -----------------------


@pytest.mark.parametrize(
    "overrides,expected_points,expected_reason",
    [
        ({"amount": 10_000.01}, 25, "High amount"),
        ({"is_foreign": True}, 15, "Foreign transaction"),
        ({"is_night_transaction": True}, 10, "Night transaction"),
        ({"previous_failed_attempts": 3}, 20, "Multiple previous failed attempts"),
        ({"device_trust_score": 39}, 20, "Low device trust score"),
        ({"merchant_category": "Crypto Exchange"}, 10, "Suspicious merchant category"),
        ({"country": "Russia"}, 10, "Unusual country or location"),
    ],
)
def test_each_signal_contributes_its_documented_weight(
    overrides, expected_points, expected_reason
):
    baseline_score = score()["risk_score"]
    result = score(**overrides)

    assert result["risk_score"] - baseline_score == expected_points
    assert expected_reason in result["reasons"]


def test_clean_transaction_scores_zero_and_says_so():
    result = score()

    assert result["risk_score"] == 0
    assert result["risk_level"] == "LOW"
    # An empty reasons list would render as a blank panel in the console; the
    # engine must state that it found nothing rather than say nothing.
    assert result["reasons"] == ["No significant risk indicators"]


# --- thresholds: the exact points where behaviour flips --------------------


@pytest.mark.parametrize(
    "amount,should_flag",
    [(9_999.99, False), (10_000.0, False), (10_000.01, True)],
)
def test_amount_threshold_is_strictly_greater_than_10000(amount, should_flag):
    """10 000 exactly is NOT high — the rule is `> 10000`, not `>=`."""
    assert ("High amount" in score(amount=amount)["reasons"]) is should_flag


@pytest.mark.parametrize("attempts,should_flag", [(2, False), (3, True), (10, True)])
def test_failed_attempts_threshold_is_three_or_more(attempts, should_flag):
    result = score(previous_failed_attempts=attempts)
    assert ("Multiple previous failed attempts" in result["reasons"]) is should_flag


@pytest.mark.parametrize("trust,should_flag", [(40, False), (39, True), (0, True)])
def test_device_trust_threshold_is_strictly_below_40(trust, should_flag):
    result = score(device_trust_score=trust)
    assert ("Low device trust score" in result["reasons"]) is should_flag


@pytest.mark.parametrize(
    "points,level",
    [
        (0, "LOW"),
        (29, "LOW"),
        (30, "MEDIUM"),
        (59, "MEDIUM"),
        (60, "HIGH"),
        (79, "HIGH"),
        (80, "CRITICAL"),
        (100, "CRITICAL"),
    ],
)
def test_risk_level_boundaries(points, level):
    assert risk_level_for_score(points) == level


# --- saturation ------------------------------------------------------------


def test_score_is_capped_at_100():
    """Every signal at once sums to 110 — the score must not exceed 100."""
    result = score(
        amount=999_999,
        is_foreign=True,
        is_night_transaction=True,
        previous_failed_attempts=9,
        device_trust_score=0,
        merchant_category="Gambling",
        country="North Korea",
    )

    assert result["risk_score"] == 100
    assert result["risk_level"] == "CRITICAL"
    assert len(result["reasons"]) == 7


# --- case and whitespace handling -----------------------------------------


@pytest.mark.parametrize(
    "category", ["crypto exchange", "Crypto Exchange", "CRYPTO EXCHANGE", "  Gambling  "]
)
def test_merchant_category_matching_ignores_case_and_padding(category):
    """The CSV import is not normalised upstream, so the engine must be."""
    assert "Suspicious merchant category" in score(merchant_category=category)["reasons"]


@pytest.mark.parametrize("country", ["russia", "Russia", "  NORTH KOREA  "])
def test_country_matching_ignores_case_and_padding(country):
    assert "Unusual country or location" in score(country=country)["reasons"]


def test_unlisted_category_and_country_are_not_flagged():
    result = score(merchant_category="Bookshop", country="Portugal")

    assert "Suspicious merchant category" not in result["reasons"]
    assert "Unusual country or location" not in result["reasons"]


# --- coercion: the engine also scores rows straight off a CSV --------------


@pytest.mark.parametrize("value", ["true", "True", "1", "yes", "Y"])
def test_boolean_flags_accept_csv_truthy_strings(value):
    assert "Foreign transaction" in score(is_foreign=value)["reasons"]


@pytest.mark.parametrize("value", ["false", "False", "0", "no", "", "nonsense"])
def test_boolean_flags_treat_anything_else_as_false(value):
    assert "Foreign transaction" not in score(is_foreign=value)["reasons"]


def test_numeric_fields_accept_strings():
    result = score(amount="25000", previous_failed_attempts="4", device_trust_score="10")

    assert "High amount" in result["reasons"]
    assert "Multiple previous failed attempts" in result["reasons"]
    assert "Low device trust score" in result["reasons"]


def test_unparseable_numbers_fall_back_without_crashing():
    """A malformed CSV cell must not take the import down."""
    result = score(amount="not-a-number", previous_failed_attempts="?")

    assert result["risk_score"] >= 0
    assert "High amount" not in result["reasons"]


def test_missing_device_trust_score_defaults_to_trusted():
    """Absent telemetry must not manufacture a risk signal out of nothing."""
    payload = {k: v for k, v in BASELINE.items() if k != "device_trust_score"}

    assert "Low device trust score" not in score_transaction(payload)["reasons"]


def test_empty_payload_is_scored_rather_than_rejected():
    result = score_transaction({})

    assert result["risk_score"] == 0
    assert result["risk_level"] == "LOW"


# --- combinations that matter to an analyst --------------------------------


def test_classic_account_takeover_pattern_reaches_critical():
    """Foreign + night + repeated failures + untrusted device on a big amount."""
    result = score(
        amount=18_500,
        is_foreign=True,
        is_night_transaction=True,
        previous_failed_attempts=4,
        device_trust_score=28,
        merchant_category="Crypto Exchange",
        country="Nigeria",
    )

    assert result["risk_level"] == "CRITICAL"
    assert result["risk_score"] >= 80


def test_large_but_otherwise_clean_transaction_is_only_medium():
    """A big legitimate purchase should not land in the critical queue."""
    result = score(amount=25_000)

    assert result["risk_score"] == 25
    assert result["risk_level"] == "LOW"


def test_reasons_are_analyst_readable_not_codes():
    """The reasons are shown verbatim in the console."""
    result = score(amount=50_000, is_foreign=True)

    for reason in result["reasons"]:
        assert reason[0].isupper()
        assert "_" not in reason
