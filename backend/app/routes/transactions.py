import csv
from datetime import datetime
import io
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.fraud_engine import score_transaction


router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def _normalize_transaction_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "transaction_id": str(data["transaction_id"]).strip(),
        "customer_id": str(data["customer_id"]).strip(),
        "amount": float(data["amount"]),
        "currency": str(data.get("currency", "USD")).strip().upper(),
        "merchant": str(data["merchant"]).strip(),
        "merchant_category": str(data["merchant_category"]).strip(),
        "country": str(data["country"]).strip(),
        "city": str(data["city"]).strip(),
        "channel": str(data["channel"]).strip().upper(),
        "transaction_date": _parse_datetime(data["transaction_date"]),
        "is_foreign": _parse_bool(data.get("is_foreign", False)),
        "is_night_transaction": _parse_bool(data.get("is_night_transaction", False)),
        "previous_failed_attempts": int(data.get("previous_failed_attempts", 0)),
        "device_trust_score": int(data.get("device_trust_score", 100)),
        "status": str(data.get("status", "NEW")).strip().upper(),
    }
    normalized.update(score_transaction(normalized))
    return normalized


def _create_case_if_needed(db: Session, transaction: models.Transaction) -> None:
    if transaction.risk_level not in {"HIGH", "CRITICAL"}:
        return

    existing = (
        db.query(models.FraudCase)
        .filter(models.FraudCase.transaction_id == transaction.id)
        .first()
    )
    if existing:
        return

    db.add(
        models.FraudCase(
            transaction_id=transaction.id,
            assigned_to="Tier 2 Fraud Operations",
            priority=transaction.risk_level,
            status="NEW",
            notes=f"Auto-created case for {transaction.risk_level.lower()} risk transaction.",
        )
    )


@router.get("", response_model=list[schemas.TransactionRead])
def list_transactions(
    risk_level: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="transaction_date"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Transaction)

    if risk_level and risk_level.upper() != "ALL":
        query = query.filter(models.Transaction.risk_level == risk_level.upper())

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Transaction.customer_id.ilike(pattern),
                models.Transaction.merchant.ilike(pattern),
                models.Transaction.transaction_id.ilike(pattern),
            )
        )

    sort_fields = {
        "amount": models.Transaction.amount,
        "risk_score": models.Transaction.risk_score,
        "date": models.Transaction.transaction_date,
        "transaction_date": models.Transaction.transaction_date,
    }
    sort_column = sort_fields.get(sort_by, models.Transaction.transaction_date)
    query = query.order_by(desc(sort_column) if sort_order.lower() == "desc" else asc(sort_column))

    return query.all()


@router.get("/{transaction_id}", response_model=schemas.TransactionRead)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.get(models.Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


@router.post("", response_model=schemas.TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    data = _normalize_transaction_data(payload.model_dump())

    existing = (
        db.query(models.Transaction)
        .filter(models.Transaction.transaction_id == data["transaction_id"])
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction already exists")

    transaction = models.Transaction(**data)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    _create_case_if_needed(db, transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/import")
async def import_transactions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are supported")

    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    imported = 0
    skipped = 0
    created_cases = 0

    for row in reader:
        data = _normalize_transaction_data(row)
        duplicate = (
            db.query(models.Transaction)
            .filter(models.Transaction.transaction_id == data["transaction_id"])
            .first()
        )
        if duplicate:
            skipped += 1
            continue

        transaction = models.Transaction(**data)
        db.add(transaction)
        db.flush()
        before_count = db.query(models.FraudCase).count()
        _create_case_if_needed(db, transaction)
        after_count = db.query(models.FraudCase).count()
        created_cases += after_count - before_count
        imported += 1

    db.commit()
    return {"imported": imported, "skipped": skipped, "created_cases": created_cases}

