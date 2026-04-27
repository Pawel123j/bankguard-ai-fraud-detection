from app.fraud_engine import score_transaction


def test_normal_transaction_should_be_low_risk():
    result = score_transaction(
        {
            "amount": 42.75,
            "is_foreign": False,
            "is_night_transaction": False,
            "previous_failed_attempts": 0,
            "device_trust_score": 92,
            "merchant_category": "Groceries",
            "country": "United States",
        }
    )

    assert result["risk_level"] == "LOW"
    assert result["risk_score"] < 30


def test_large_foreign_night_transaction_should_be_high_or_critical():
    result = score_transaction(
        {
            "amount": 18500,
            "is_foreign": True,
            "is_night_transaction": True,
            "previous_failed_attempts": 4,
            "device_trust_score": 28,
            "merchant_category": "Crypto Exchange",
            "country": "Nigeria",
        }
    )

    assert result["risk_level"] in {"HIGH", "CRITICAL"}
    assert result["risk_score"] >= 60
    assert "High amount" in result["reasons"]


def test_low_device_trust_score_should_increase_risk_score():
    trusted = score_transaction(
        {
            "amount": 120,
            "is_foreign": False,
            "is_night_transaction": False,
            "previous_failed_attempts": 0,
            "device_trust_score": 85,
            "merchant_category": "Dining",
            "country": "United States",
        }
    )
    untrusted = score_transaction(
        {
            "amount": 120,
            "is_foreign": False,
            "is_night_transaction": False,
            "previous_failed_attempts": 0,
            "device_trust_score": 25,
            "merchant_category": "Dining",
            "country": "United States",
        }
    )

    assert untrusted["risk_score"] > trusted["risk_score"]
    assert "Low device trust score" in untrusted["reasons"]

