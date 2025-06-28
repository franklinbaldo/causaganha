"""Pydantic models for analytics features."""

from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel


class OutcomeTrend(BaseModel):
    """Aggregated decision outcomes for a specific date."""

    date: date
    procedente: int
    improcedente: int


class RatingPoint(BaseModel):
    """Single rating measurement for a lawyer."""

    match_id: int
    rating: float


class RatingTrend(BaseModel):
    """Rating history of a lawyer across matches."""

    lawyer_id: str
    history: List[RatingPoint]
