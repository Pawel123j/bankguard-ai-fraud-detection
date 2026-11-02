from datetime import datetime, timezone

import pytest
from app import models
from app.database import SessionLocal, engine
from app.fraud_engine import score_transaction
from app.time_utils import utc_naive, utc_now_naive
from test_import import csv_bytes, sample_row


@pytest.mark.parametrize("source,expected", [
    ("2026-10-25T12:00:00+02:00", "2026-10-25T10:00:00"),
    ("2026-10-25T10:00:00Z", "2026-10-25T10:00:00"),
    ("2026-01-01T00:30:00+02:00", "2025-12-31T22:30:00"),
    ("2026-10-25T02:30:00+02:00", "2026-10-25T00:30:00"),
    ("2026-10-25T02:30:00+01:00", "2026-10-25T01:30:00"),
    ("2026-10-25T10:00:00", "2026-10-25T10:00:00"),
])
def test_utc_contract(source, expected):
    assert utc_naive(source) == datetime.fromisoformat(expected)
    assert utc_naive(datetime.fromisoformat(source.replace("Z", "+00:00"))) == datetime.fromisoformat(expected)


def test_utc_now_is_naive_utc_for_sqlite():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    current = utc_now_naive()
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert before <= current <= after
    assert current.tzinfo is None


def test_api_csv_and_currency_report_share_contract(client, auth_headers):
    first = {**sample_row(), "transaction_id": "UTC-USD", "amount": "100", "currency": "USD", "transaction_date": "2026-10-25T12:00:00+02:00"}
    second = {**first, "transaction_id": "UTC-PLN", "currency": "PLN", "transaction_date": "2026-10-25T10:00:00Z"}
    response = client.post("/api/transactions", json=first, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["transaction_date"] == "2026-10-25T10:00:00Z"
    response = client.post("/api/transactions/import", headers=auth_headers, files={"file": ("sample.csv", csv_bytes([second]), "text/csv")})
    assert response.status_code == 200
    rows = client.get("/api/transactions", headers=auth_headers).json()
    assert len({row["transaction_date"] for row in rows}) == 1
    summary = client.get("/api/reports/summary", headers=auth_headers).json()
    assert "total_amount" not in summary
    assert summary["amounts_by_currency"] == [
        {"currency": "PLN", "total_amount": 100.0, "high_risk_amount": 0.0},
        {"currency": "USD", "total_amount": 100.0, "high_risk_amount": 0.0},
    ]


def test_currency_thresholds_are_explicit():
    assert score_transaction({"amount": 10001, "currency": "USD"})["risk_score"] == 25
    assert score_transaction({"amount": 40004, "currency": "PLN"})["risk_score"] == 25
    assert score_transaction({"amount": 10001, "currency": "PLN"})["risk_score"] == 0
    assert "manual review" in score_transaction({"amount": 100000, "currency": "JPY"})["reasons"][0]


def test_reseed_and_database_reopen_preserve_analyst_work(client, monkeypatch):
    from seed import seed
    monkeypatch.setenv("BANKGUARD_DEMO_PASSWORD", "isolated-seed-test-password")
    seed()
    with SessionLocal() as db:
        case = db.query(models.FraudCase).first()
        case.notes = "Analyst work must survive"
        case.status = "INVESTIGATING"
        case_id = case.id
        counts = (db.query(models.Transaction).count(), db.query(models.FraudCase).count())
        db.commit()
    engine.dispose()
    seed()
    with SessionLocal() as db:
        assert (db.query(models.Transaction).count(), db.query(models.FraudCase).count()) == counts
        assert db.get(models.FraudCase, case_id).notes == "Analyst work must survive"
        assert db.get(models.FraudCase, case_id).status == "INVESTIGATING"
