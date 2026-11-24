import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from app import models, schemas  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.routes.transactions import _normalize_transaction_data  # noqa: E402

CSV_PATH = ROOT / "data" / "sample_transactions.csv"


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    """Validate and score a seed row exactly like the API import does."""
    row = {**row, "status": (row.get("status") or "NEW").strip().upper() or "NEW"}
    payload = schemas.TransactionCreate.model_validate(row)
    return _normalize_transaction_data(payload.model_dump())


def seed() -> None:
    init_db()  # also adds columns introduced after an existing database was created
    db = SessionLocal()
    try:
        with CSV_PATH.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if db.query(models.Transaction).filter_by(transaction_id=row["transaction_id"].strip()).first():
                    continue
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

        _seed_analyst(db)

        db.commit()
        print("Added missing demo transactions; existing transactions, cases and notes preserved.")
    finally:
        db.close()


def _seed_analyst(db) -> None:
    """Create the console login.

    The password is NOT hardcoded. It comes from BANKGUARD_DEMO_PASSWORD, and
    when that is unset a random one is generated and printed once — so a fresh
    clone is usable without a credential ever entering source control.
    """
    import os
    import secrets

    from app.security import hash_password

    email = os.getenv("BANKGUARD_DEMO_EMAIL", "analyst@bankguard.ai").lower()
    if db.query(models.Analyst).filter(models.Analyst.email == email).first():
        print(f"Analyst {email} already exists — leaving the password alone.")
        return

    password = os.getenv("BANKGUARD_DEMO_PASSWORD")
    generated = password is None
    if generated:
        password = secrets.token_urlsafe(12)

    db.add(
        models.Analyst(
            email=email,
            full_name=os.getenv("BANKGUARD_DEMO_NAME", "Fraud Analyst"),
            password_hash=hash_password(password),
        )
    )

    print(f"\nAnalyst account: {email}")
    if generated:
        print(f"Generated password: {password}")
        print("Shown once and not stored anywhere else. Set BANKGUARD_DEMO_PASSWORD to choose your own.\n")
    else:
        print("Password taken from BANKGUARD_DEMO_PASSWORD.\n")



if __name__ == "__main__":
    seed()

