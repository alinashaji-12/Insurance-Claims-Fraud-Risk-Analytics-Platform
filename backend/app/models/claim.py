"""SQLAlchemy Claim model."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Claim(Base):
    """Insurance claim record with fraud scoring fields."""

    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_number: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    claimant_name: Mapped[str] = mapped_column(String(128), nullable=False)
    claimant_phone: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    claimant_address: Mapped[str] = mapped_column(
        String(256), index=True, nullable=False
    )
    bank_account: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    vehicle_vin: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    repair_shop: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fraud_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fraud_label: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    # Extra features retained for ML (from source dataset)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vehicle_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_price_band: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accident_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fault: Mapped[str | None] = mapped_column(String(64), nullable=True)
    past_number_of_claims: Mapped[str | None] = mapped_column(String(64), nullable=True)
    age_of_vehicle: Mapped[str | None] = mapped_column(String(64), nullable=True)
    police_report_filed: Mapped[str | None] = mapped_column(String(16), nullable=True)
    witness_present: Mapped[str | None] = mapped_column(String(16), nullable=True)
    base_policy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    days_policy_claim: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address_change_claim: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deductible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    driver_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    make: Mapped[str | None] = mapped_column(String(64), nullable=True)
