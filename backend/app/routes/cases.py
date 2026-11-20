from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.security import get_current_analyst, require_writer
from app.time_utils import utc_now_naive

router = APIRouter(
    prefix="/api/cases", tags=["cases"],
    # Zależność na routerze, nie na pojedynczych trasach: nowy endpoint
    # nie może przez przeoczenie zostać bez uwierzytelnienia.
    dependencies=[Depends(get_current_analyst)],
)


@router.get("", response_model=list[schemas.FraudCaseRead])
def list_cases(
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.FraudCase)
        .options(joinedload(models.FraudCase.transaction))
        .order_by(models.FraudCase.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/{case_id}", response_model=schemas.FraudCaseRead)
def update_case(
    case_id: int,
    payload: schemas.FraudCaseUpdate,
    db: Session = Depends(get_db),
    analyst: models.Analyst = Depends(require_writer),
):
    fraud_case = (
        db.query(models.FraudCase)
        .options(joinedload(models.FraudCase.transaction))
        .filter(models.FraudCase.id == case_id)
        .first()
    )
    if not fraud_case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(fraud_case, field, value)

    if payload.status == "INVESTIGATING" and fraud_case.transaction:
        fraud_case.transaction.status = "ESCALATED"
    elif payload.status == "RESOLVED" and fraud_case.transaction:
        fraud_case.transaction.status = "REVIEWED"
    elif payload.status == "FALSE_POSITIVE" and fraud_case.transaction:
        fraud_case.transaction.status = "CLEARED"

    fraud_case.updated_at = utc_now_naive()
    fraud_case.updated_by = analyst.email
    db.commit()
    db.refresh(fraud_case)
    return fraud_case

