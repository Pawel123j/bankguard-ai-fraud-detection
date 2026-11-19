from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.time_utils import utc_iso

Channel = Literal["CARD", "TRANSFER", "ATM", "ONLINE"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
TransactionStatus = Literal["NEW", "REVIEWED", "ESCALATED", "CLEARED"]
CaseStatus = Literal["NEW", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"]


class TransactionBase(BaseModel):
    transaction_id: str = Field(min_length=3, max_length=64)
    customer_id: str = Field(min_length=3, max_length=64)
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    merchant: str = Field(min_length=2, max_length=160)
    merchant_category: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=80)
    channel: Channel
    transaction_date: datetime
    is_foreign: bool = False
    is_night_transaction: bool = False
    previous_failed_attempts: int = Field(default=0, ge=0)
    device_trust_score: int = Field(default=100, ge=0, le=100)

    @field_validator("currency")
    @classmethod
    def currency_code(cls, value: str) -> str:
        value = value.upper()
        if not value.isascii() or not value.isalpha():
            raise ValueError("Use a three-letter currency code")
        return value


class TransactionCreate(TransactionBase):
    status: TransactionStatus = "NEW"


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_score: int
    risk_level: RiskLevel
    reasons: list[str]
    status: TransactionStatus

    @field_serializer("transaction_date")
    def serialize_date(self, value: datetime) -> str:
        return utc_iso(value)


class FraudCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    assigned_to: str
    status: CaseStatus
    priority: RiskLevel
    notes: str
    created_at: datetime
    updated_at: datetime
    updated_by: str | None = None
    transaction: TransactionRead | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_date(self, value: datetime) -> str:
        return utc_iso(value)


class FraudCaseUpdate(BaseModel):
    assigned_to: str | None = Field(default=None, max_length=120)
    status: CaseStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)


class DashboardStats(BaseModel):
    total_transactions: int
    high_risk_transactions: int
    critical_alerts: int
    open_fraud_cases: int
    risk_distribution: dict[str, int]
    channel_distribution: dict[str, int]
    recent_alerts: list[TransactionRead]

