import csv
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.fraud_engine import score_transaction  # noqa: E402


CSV_PATH = ROOT / "data" / "sample_transactions.csv"


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    transaction = {
        "transaction_id": row["transaction_id"].strip(),
        "customer_id": row["customer_id"].strip(),
        "amount": float(row["amount"]),
        "currency": row["currency"].strip().upper(),
        "merchant": row["merchant"].strip(),
        "merchant_category": row["merchant_category"].strip(),
        "country": row["country"].strip(),
        "city": row["city"].strip(),
        "channel": row["channel"].strip().upper(),
        "transaction_date": datetime.fromisoformat(row["transaction_date"]),
        "is_foreign": parse_bool(row["is_foreign"]),
        "is_night_transaction": parse_bool(row["is_night_transaction"]),
        "previous_failed_attempts": int(row["previous_failed_attempts"]),
        "device_trust_score": int(row["device_trust_score"]),
        "status": row.get("status", "NEW").strip().upper() or "NEW",
    }
    transaction.update(score_transaction(transaction))
    return transaction


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(models.FraudCase).delete()
        db.query(models.Transaction).delete()

        with CSV_PATH.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                transaction = models.Transaction(**normalize_row(row))
                db.add(transaction)
                db.flush()

                if transaction.risk_level in {"HIGH", "CRITICAL"}:
                    db.add(
                        models.FraudCase(
                            transaction_id=transaction.id,
                            assigned_to="Tier 2 Fraud Operations",
                            priority=transaction.risk_level,
                            status="NEW",
                            notes=f"Seeded alert for {transaction.risk_level.lower()} risk transaction.",
                        )
                    )

        db.commit()
        print("Seeded BankGuard AI database from sample_transactions.csv")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

