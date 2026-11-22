"""Request / response contract for the scoring API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

DECISION_NOTE = (
    "Decision support only. The lender makes the decision, and a person reviews every case "
    "that is not a clear approve."
)
DATA_NOTE = "The model was built on synthetic data. Its accuracy on real vendors is not yet known."


class DailyRecord(BaseModel):
    day: int = Field(..., ge=0, description="Integer day index; one record per day. Missing days count as zero inflow.")
    n_txn: int = Field(..., ge=0)
    inflow: float = Field(..., ge=0, description="Total UPI receipts that day, rupees")


class LoanTerms(BaseModel):
    amount: float = Field(..., gt=0, le=5_000_000)
    tenure_months: int = Field(..., ge=1, le=60)
    emi: float | None = Field(None, gt=0, description="Monthly instalment. Computed from annual_rate if omitted.")
    annual_rate: float | None = Field(None, gt=0, lt=1)

    @model_validator(mode="after")
    def _need_emi_or_rate(self) -> "LoanTerms":
        if self.emi is None and self.annual_rate is None:
            raise ValueError("provide emi or annual_rate")
        return self

    def resolved_emi(self) -> float:
        if self.emi is not None:
            return float(self.emi)
        r = float(self.annual_rate) / 12  # type: ignore[arg-type]
        f = (1 + r) ** self.tenure_months
        return round(self.amount * r * f / (f - 1), 0)


class ScoreRequest(BaseModel):
    vendor_id: str = Field(..., min_length=1, max_length=64)
    consent_given: bool
    loan: LoanTerms
    daily_records: list[DailyRecord] = Field(..., max_length=1000)
    vendor_type: str | None = Field(None, max_length=40, description="Optional; reporting only, not a model input")


class Reason(BaseModel):
    code: str
    feature: str
    direction: Literal["increases_risk", "reduces_risk"]
    impact_points: int
    text_en: str
    text_hi: str


class ScoreResponse(BaseModel):
    request_id: str
    probability_of_default: float
    score: int
    band: Literal["approve", "review", "decline"]
    human_review_required: bool
    reasons: list[Reason]
    strengths: list[Reason]
    features: dict[str, float]
    key_values: dict[str, float | int]
    emi_used: float
    days_used: int
    model_version: str
    decision_note: str = DECISION_NOTE
    data_note: str = DATA_NOTE
