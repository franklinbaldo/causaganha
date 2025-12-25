
from datetime import date

import pytest
from pydantic import ValidationError

from causaganha.analysis.models import DecisionAnalysis, Outcome


def test_decision_analysis_model_creation():
    """Test successful creation of a DecisionAnalysis model."""
    analysis = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="The appeal was granted.",
        judge_name="Dr. Smith",
        confidence_score=0.95,
        winner_lawyer_oab="12345",
        winner_lawyer_state="SP",
        winner_party_name="John Doe",
        loser_lawyer_oab="54321",
        loser_lawyer_state="RJ",
        loser_party_name="Jane Doe",
        decision_type="Acórdão",
        decision_reasoning="The lower court's decision was overturned.",
        acordao="Full text of the acordão...",
        tribunal="TJSP",
        decision_date=date(2024, 1, 1),
    )
    assert analysis.outcome == Outcome.WIN
    assert analysis.tribunal == "TJSP"
    assert analysis.acordao is not None


def test_decision_analysis_missing_required_fields():
    """Test that missing required fields raise a validation error."""
    with pytest.raises(ValidationError):
        DecisionAnalysis(
            outcome=Outcome.LOSS,
            # Missing summary and confidence_score
        )

def test_decision_analysis_optional_fields():
    """Test that optional fields can be None."""
    analysis = DecisionAnalysis(
        outcome=Outcome.UNKNOWN,
        summary="Analysis could not be completed.",
        confidence_score=0.1,
        # All other fields are optional or have defaults
    )
    assert analysis.judge_name is None
    assert analysis.acordao is None
    assert analysis.tribunal is None
    assert analysis.decision_date is None

def test_decision_analysis_invalid_confidence_score():
    """Test that confidence_score outside the valid range raises an error."""
    with pytest.raises(ValidationError):
        DecisionAnalysis(
            outcome=Outcome.WIN,
            summary="A summary.",
            confidence_score=1.5,
        )

    with pytest.raises(ValidationError):
        DecisionAnalysis(
            outcome=Outcome.WIN,
            summary="A summary.",
            confidence_score=-0.5,
        )
