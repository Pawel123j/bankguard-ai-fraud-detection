from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=schemas.DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    total_transactions = db.query(func.count(models.Transaction.id)).scalar() or 0
    high_risk_transactions = (
        db.query(func.count(models.Transaction.id))
        .filter(models.Transaction.risk_level.in_(["HIGH", "CRITICAL"]))
        .scalar()
        or 0
    )
    critical_alerts = (
        db.query(func.count(models.Transaction.id))
        .filter(models.Transaction.risk_level == "CRITICAL")
        .scalar()
        or 0
    )
    open_fraud_cases = (
        db.query(func.count(models.FraudCase.id))
        .filter(models.FraudCase.status.in_(["NEW", "INVESTIGATING"]))
        .scalar()
        or 0
    )

    risk_distribution = {level: 0 for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
    for level, count in db.query(models.Transaction.risk_level, func.count(models.Transaction.id)).group_by(
        models.Transaction.risk_level
    ):
        risk_distribution[level] = count

    channel_distribution = {channel: 0 for channel in ["CARD", "TRANSFER", "ATM", "ONLINE"]}
    for channel, count in db.query(models.Transaction.channel, func.count(models.Transaction.id)).group_by(
        models.Transaction.channel
    ):
        channel_distribution[channel] = count

    recent_alerts = (
        db.query(models.Transaction)
        .filter(models.Transaction.risk_level.in_(["HIGH", "CRITICAL"]))
        .order_by(models.Transaction.transaction_date.desc())
        .limit(6)
        .all()
    )

    return {
        "total_transactions": total_transactions,
        "high_risk_transactions": high_risk_transactions,
        "critical_alerts": critical_alerts,
        "open_fraud_cases": open_fraud_cases,
        "risk_distribution": risk_distribution,
        "channel_distribution": channel_distribution,
        "recent_alerts": recent_alerts,
    }

