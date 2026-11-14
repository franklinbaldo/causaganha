"""Versioned, offline transcript contract for the experimental legal arena."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1)]
UnitScore = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Level(StrEnum):
    ADVOCACIA = "advocacia"
    JUIZO = "juizo"
    TRIBUNAL = "tribunal"
    STJ = "stj"
    STF = "stf"


class Competitor(Record):
    id: Identifier
    model: Identifier
    revision: Identifier


class Rules(Record):
    min_cases: int = Field(default=3, ge=1)
    promotion_score: UnitScore = 0.6
    court_seats: int = Field(default=100, ge=1)
    stj_seats: int = Field(default=35, ge=1)
    stf_seats: int = Field(default=11, ge=1)


class Disposition(Record):
    """Outcome of the ORIGINAL claim, never the polarity of an appeal."""

    merits: bool
    claimant_share: UnitScore | None

    @model_validator(mode="after")
    def consistent(self) -> Disposition:
        if self.merits != (self.claimant_share is not None):
            msg = "Mérito exige claimant_share; inadmissibilidade exige null."
            raise ValueError(msg)
        return self


class Submission(Record):
    competitor: Identifier
    text: Identifier


class Vote(Submission):
    disposition: Disposition


class Panel(Record):
    level: Level
    votes: list[Vote] = Field(min_length=1)

    @model_validator(mode="after")
    def judicial(self) -> Panel:
        if self.level == Level.ADVOCACIA:
            msg = "Advocacia não é órgão julgador."
            raise ValueError(msg)
        ids = [vote.competitor for vote in self.votes]
        if len(ids) != len(set(ids)):
            msg = "Competidor repetido no colegiado."
            raise ValueError(msg)
        return self


class Anchor(Record):
    court: Level
    source_url: Annotated[str, Field(pattern=r"^https://")]
    document_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    disposition: Disposition

    @model_validator(mode="after")
    def superior(self) -> Anchor:
        if self.court not in {Level.STJ, Level.STF}:
            msg = "A âncora deve ser STJ ou STF."
            raise ValueError(msg)
        return self


class Match(Record):
    case_id: Identifier
    claimant: Submission
    defendant: Submission
    panels: list[Panel] = Field(default_factory=list)
    anchor: Anchor


class Round(Record):
    id: Identifier
    matches: list[Match] = Field(min_length=1)


class Season(Record):
    schema_version: int = Field(default=1, ge=1, le=1)
    demonstration: bool = False
    rules: Rules = Field(default_factory=Rules)
    competitors: list[Competitor] = Field(min_length=2)
    rounds: list[Round] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_ids(self) -> Season:
        for ids in (
            [entry.id for entry in self.competitors],
            [entry.id for entry in self.rounds],
            [(entry.model, entry.revision) for entry in self.competitors],
        ):
            if len(ids) != len(set(ids)):
                msg = "Identificadores duplicados."
                raise ValueError(msg)
        return self
