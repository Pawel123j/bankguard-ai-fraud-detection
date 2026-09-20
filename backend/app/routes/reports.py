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
    total_amount = db.query(func.coalesce(func.sum(models.Transaction.amount), 0)).scalar() or 0
    high_risk_amount = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0))
        .filter(models.Transaction.risk_level.in_(["HIGH", "CRITICAL"]))
        .scalar()
        or 0
    )
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
        f"Estimated exposure in high-risk transactions is {high_risk_amount:,.2f}."
    )

    return {
        "total_transactions": total_transactions,
        "total_amount": round(float(total_amount), 2),
        "high_risk_amount": round(float(high_risk_amount), 2),
        "open_cases": cases_open,
        "risk_distribution": risk_distribution,
        "channel_distribution": channel_distribution,
        "top_alert_countries": countries,
        "executive_summary": executive_summary,
    }

