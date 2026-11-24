"""Transparent rule engine for transaction risk scoring.

Rule set revision 2026-11. Sources behind the 2026-11 additions:

- FATF plenary outcomes, 30 Oct 2026: high-risk jurisdictions subject to a call
  for action and the 18 jurisdictions under increased monitoring.
- UK Finance Annual Fraud Report 2026: authorised push payment (APP) losses up
  19%, investment scams the largest APP category, "malicious payee" activity.
- BIK Raport Antyfraudowy 2026: BLIK-code requests from hijacked social-media
  accounts ("na znajomego") are the most common scam Poles encounter.
- Europol IOCTA 2026: SIM-swap / SIM-farm account takeover, mule networks.
- Industry guidance on scam detection: remote-access tools and an active phone
  call during a payment are standard bank-impersonation ("safe account") signals.

Weights and thresholds are illustrative policy examples, not a calibrated model.
Jurisdiction lists change at every FATF plenary (Feb/Jun/Oct) and must be
reviewed then.
"""

from typing import Any

RULESET_VERSION = "2026-11"

# Illustrative policy thresholds, not live FX quotes or calibrated fraud models.
HIGH_AMOUNT_THRESHOLDS = {"USD": 10000, "EUR": 9000, "GBP": 8000, "PLN": 40000}


SUSPICIOUS_MERCHANT_CATEGORIES = {
    "crypto exchange",
    "crypto atm",
    "investment platform",
    "gambling",
    "gift cards",
    "money transfer",
    "wire transfer",
    "luxury goods",
    "electronics",
}

# Categories through which investment / "pig butchering" scams cash out.
INVESTMENT_SCAM_CATEGORIES = {"crypto exchange", "crypto atm", "investment platform"}

# FATF "black list" — call for action, plenary of 28-30 October 2026.
FATF_CALL_FOR_ACTION = {
    "iran",
    "north korea",
    "dprk",
    "democratic people's republic of korea",
    "myanmar",
    "burma",
}

# FATF "grey list" — jurisdictions under increased monitoring, 30 October 2026.
# Bulgaria, Côte d'Ivoire, DR Congo and Monaco were removed at that plenary.
FATF_INCREASED_MONITORING = {
    "angola",
    "bolivia",
    "bosnia and herzegovina",
    "cameroon",
    "haiti",
    "iraq",
    "kenya",
    "kuwait",
    "lao pdr",
    "laos",
    "lebanon",
    "nepal",
    "papua new guinea",
    "south sudan",
    "syria",
    "venezuela",
    "vietnam",
    "viet nam",
    "virgin islands (uk)",
    "british virgin islands",
    "yemen",
}

# Under broad EU sanctions regimes; not FATF-listed but restricted for EU banks.
SANCTIONED_JURISDICTIONS = {"russia", "belarus"}

UNKNOWN_LOCATIONS = {"unknown"}

# Recipient accounts younger than this are a common money-mule indicator.
NEW_PAYEE_ACCOUNT_DAYS = 30


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


def _as_optional_int(value: Any) -> int | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _jurisdiction_signal(country: str) -> tuple[int, str] | None:
    if country in FATF_CALL_FOR_ACTION:
        return 20, "FATF high-risk jurisdiction (call for action)"
    if country in SANCTIONED_JURISDICTIONS:
        return 15, "Sanctioned jurisdiction"
    if country in FATF_INCREASED_MONITORING:
        return 10, "FATF jurisdiction under increased monitoring"
    if country in UNKNOWN_LOCATIONS:
        return 10, "Unknown location"
    return None


def score_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    """Score a transaction from 0 to 100 and return analyst-readable reasons."""
    score = 0
    reasons: list[str] = []

    def flag(points: int, reason: str) -> None:
        nonlocal score
        score += points
        reasons.append(reason)

    amount = _as_float(transaction.get("amount"))
    is_foreign = _as_bool(transaction.get("is_foreign"))
    is_night = _as_bool(transaction.get("is_night_transaction"))
    failed_attempts = _as_int(transaction.get("previous_failed_attempts"))
    device_trust_score = _as_int(transaction.get("device_trust_score"), 100)
    merchant_category = str(transaction.get("merchant_category", "")).strip().lower()
    country = str(transaction.get("country", "")).strip().lower()
    channel = str(transaction.get("channel", "")).strip().upper()

    # Signals added in rule set 2026-11. All optional: older CSVs and API
    # clients that do not send them keep the previous scores.
    is_new_payee = _as_bool(transaction.get("is_new_payee", False))
    remote_access = _as_bool(transaction.get("remote_access_detected", False))
    active_call = _as_bool(transaction.get("active_call_during_session", False))
    recent_sim_swap = _as_bool(transaction.get("recent_sim_swap", False))
    payee_account_age = _as_optional_int(transaction.get("payee_account_age_days"))

    # --- single-signal rules ---------------------------------------------

    currency = str(transaction.get("currency", "USD")).strip().upper()
    threshold = HIGH_AMOUNT_THRESHOLDS.get(currency)
    if threshold is None:
        reasons.append(f"Amount rule unavailable for {currency}; manual review required")
    elif amount > threshold:
        flag(25, "High amount")

    if is_foreign:
        flag(15, "Foreign transaction")

    if is_night:
        flag(10, "Night transaction")

    if failed_attempts >= 3:
        flag(20, "Multiple previous failed attempts")

    if device_trust_score < 40:
        flag(20, "Low device trust score")

    if merchant_category in SUSPICIOUS_MERCHANT_CATEGORIES:
        flag(10, "Suspicious merchant category")

    jurisdiction = _jurisdiction_signal(country)
    if jurisdiction:
        flag(*jurisdiction)

    if is_new_payee:
        flag(15, "First payment to a new payee")

    if payee_account_age is not None and payee_account_age < NEW_PAYEE_ACCOUNT_DAYS:
        flag(15, "Recipient account opened recently (possible money mule)")

    if remote_access:
        flag(25, "Remote-access or screen-sharing tool active during session")

    if active_call:
        flag(15, "Customer on an active phone call during payment")

    if recent_sim_swap:
        flag(20, "SIM card swapped recently")

    # --- scam typologies: combinations that are stronger than their parts --

    if (active_call or remote_access) and is_new_payee and channel in {"TRANSFER", "BLIK"}:
        flag(15, "Pattern: possible bank-impersonation (safe account) scam")

    if recent_sim_swap and (device_trust_score < 40 or failed_attempts >= 3):
        flag(10, "Pattern: possible account takeover")

    if channel == "BLIK" and is_new_payee:
        flag(10, "Pattern: BLIK payment to new recipient (friend-impersonation scam)")

    if is_new_payee and merchant_category in INVESTMENT_SCAM_CATEGORIES:
        flag(10, "Pattern: possible investment scam")

    score = min(score, 100)

    if not reasons:
        reasons.append("No significant risk indicators")

    return {
        "risk_score": score,
        "risk_level": risk_level_for_score(score),
        "reasons": reasons,
    }
