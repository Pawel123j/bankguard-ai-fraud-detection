from typing import Any


SUSPICIOUS_MERCHANT_CATEGORIES = {
    "crypto exchange",
    "gambling",
    "money transfer",
    "wire transfer",
    "luxury goods",
    "electronics",
}

UNUSUAL_COUNTRIES = {
    "belarus",
    "iran",
    "north korea",
    "nigeria",
    "russia",
    "unknown",
}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def risk_level_for_score(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def score_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    """Score a transaction from 0 to 100 and return analyst-readable reasons."""
    score = 0
    reasons: list[str] = []

    amount = _as_float(transaction.get("amount"))
    is_foreign = _as_bool(transaction.get("is_foreign"))
    is_night = _as_bool(transaction.get("is_night_transaction"))
    failed_attempts = _as_int(transaction.get("previous_failed_attempts"))
    device_trust_score = _as_int(transaction.get("device_trust_score"), 100)
    merchant_category = str(transaction.get("merchant_category", "")).strip().lower()
    country = str(transaction.get("country", "")).strip().lower()

    if amount > 10000:
        score += 25
        reasons.append("High amount")

    if is_foreign:
        score += 15
        reasons.append("Foreign transaction")

    if is_night:
        score += 10
        reasons.append("Night transaction")

    if failed_attempts >= 3:
        score += 20
        reasons.append("Multiple previous failed attempts")

    if device_trust_score < 40:
        score += 20
        reasons.append("Low device trust score")

    if merchant_category in SUSPICIOUS_MERCHANT_CATEGORIES:
        score += 10
        reasons.append("Suspicious merchant category")

    if country in UNUSUAL_COUNTRIES:
        score += 10
        reasons.append("Unusual country or location")

    score = min(score, 100)

    if not reasons:
        reasons.append("No significant risk indicators")

    return {
        "risk_score": score,
        "risk_level": risk_level_for_score(score),
        "reasons": reasons,
    }

