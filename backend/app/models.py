from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.time_utils import utc_now_naive


class Analyst(Base):
    """A fraud analyst who can sign in to the console.

    Introduced together with real JWT auth. Previously the only "account" was
    an email/password pair compared inline in the login route, which meant the
    credentials lived in source control and could not be rotated, disabled or
    added to without a deploy.
    """

    __tablename__ = "analysts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(160), nullable=False, default="Fraud Analyst")
    # bcrypt hash — never the password itself.
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    # BG-01: "analyst" może zmieniać dane; "viewer" ma dostęp tylko do odczytu.
    role = Column(String(20), nullable=False, default="analyst")
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    merchant = Column(String(160), nullable=False)
    merchant_category = Column(String(100), nullable=False)
    country = Column(String(80), nullable=False)
    city = Column(String(80), nullable=False)
    channel = Column(String(20), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    is_foreign = Column(Boolean, nullable=False, default=False)
    is_night_transaction = Column(Boolean, nullable=False, default=False)
    previous_failed_attempts = Column(Integer, nullable=False, default=0)
    device_trust_score = Column(Integer, nullable=False, default=100)
    # Rule set 2026-11: scam and account-takeover signals from the payment session.
    is_new_payee = Column(Boolean, nullable=False, default=False)
    payee_account_age_days = Column(Integer, nullable=True)
    remote_access_detected = Column(Boolean, nullable=False, default=False)
    active_call_during_session = Column(Boolean, nullable=False, default=False)
    recent_sim_swap = Column(Boolean, nullable=False, default=False)
    risk_score = Column(Integer, nullable=False, default=0)
    risk_level = Column(String(20), nullable=False, default="LOW", index=True)
    reasons = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="NEW", index=True)

    cases = relationship("FraudCase", back_populates="transaction", cascade="all, delete-orphan")


class FraudCase(Base):
    __tablename__ = "fraud_cases"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    assigned_to = Column(String(120), nullable=False, default="Fraud Operations")
    status = Column(String(30), nullable=False, default="NEW", index=True)
    priority = Column(String(20), nullable=False, default="LOW", index=True)
    notes = Column(Text, nullable=False, default="")
    # BG-01: kto ostatnio zmienił sprawę (rozliczalność decyzji analityków).
    updated_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now_naive)
    updated_at = Column(DateTime, nullable=False, default=utc_now_naive, onupdate=utc_now_naive)

    transaction = relationship("Transaction", back_populates="cases")

