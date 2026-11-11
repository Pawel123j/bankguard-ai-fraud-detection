from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import get_current_analyst

router = APIRouter(
    prefix="/api/reports", tags=["reports"],
    # Zależność na routerze, nie na pojedynczych trasach: nowy endpoint
    # nie może przez przeoczenie zostać bez uwierzytelnienia.
    dependencies=[Depends(get_current_analyst)],
)


@router.get("/summary")
def report_summary(db: Session = Depends(get_db)):
    total_transactions = db.query(func.count(models.Transaction.id)).scalar() or 0
    # Decimal aggregation per currency avoids presenting mixed units as money.
    totals: dict[str, dict[str, Decimal]] = {}
    for amount, currency, level in db.query(models.Transaction.amount, models.Transaction.currency, models.Transaction.risk_level):
        bucket = totals.setdefault(currency, {"total_amount": Decimal(0), "high_risk_amount": Decimal(0)})
        bucket["total_amount"] += Decimal(str(amount))
        if level in {"HIGH", "CRITICAL"}:
            bucket["high_risk_amount"] += Decimal(str(amount))
    amounts_by_currency = [
        {"currency": currency, **{key: float(value.quantize(Decimal("0.01"))) for key, value in values.items()}}
        for currency, values in sorted(totals.items())
    ]
    cases_open = (
        db.query(func.count(models.FraudCase.id))
        .filter(models.FraudCase.status.in_(["NEW", "INVESTIGATING"]))
        .scalar()
        or 0
    )

    risk_distribution = {
        level: count
        for level, count in db.query(models.Transaction.risk_level, func.count(models.Transaction.id)).group_by(
            models.Transaction.risk_level
        )
    }
    channel_distribution = {
        channel: count
        for channel, count in db.query(models.Transaction.channel, func.count(models.Transaction.id)).group_by(
            models.Transaction.channel
        )
    }
    countries = [
        {"country": country, "alerts": count}
        for country, count in db.query(models.Transaction.country, func.count(models.Transaction.id))
        .filter(models.Transaction.risk_level.in_(["HIGH", "CRITICAL"]))
        .group_by(models.Transaction.country)
        .order_by(func.count(models.Transaction.id).desc())
        .limit(5)
    ]

    high_and_critical = sum(risk_distribution.get(level, 0) for level in ["HIGH", "CRITICAL"])
    executive_summary = (
        f"BankGuard AI reviewed {total_transactions} transactions with "
        f"{high_and_critical} high-priority alerts and {cases_open} open fraud cases. "
        "Amounts are reported per currency without FX conversion. Rule-based alerts are not confirmed fraud."
    )

    return {
        "total_transactions": total_transactions,
        "amounts_by_currency": amounts_by_currency,
        "open_cases": cases_open,
        "risk_distribution": risk_distribution,
        "channel_distribution": channel_distribution,
        "top_alert_countries": countries,
        "executive_summary": executive_summary,
    }

