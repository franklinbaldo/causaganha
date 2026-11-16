"""Metropolis exploration of a fixed, finite factual space.

Target: uniform over admissible assignments, tilted by exp(beta * disagreement).
Predictions must be obtained on the same public factual input, outside this sampler.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from statistics import pvariance
from typing import Annotated

from pydantic import Field, model_validator

from causaganha.arena.formal import FormalCase, case_digest, evaluate
from causaganha.arena.models import Identifier, Record, UnitScore


def disagreement(predictions: list[float]) -> float:
    if len(predictions) < 2 or any(not math.isfinite(p) or not 0 <= p <= 1 for p in predictions):
        msg = "São necessárias previsões finitas de pelo menos dois modelos, entre 0 e 1."
        raise ValueError(msg)
    return 4 * pvariance(predictions)


def sample(
    case: FormalCase,
    predict: Callable[[dict[str, bool]], list[float]],
    *,
    steps: int = 100,
    beta: float = 5.0,
    seed: int = 0,
) -> list[dict]:
    if not 1 <= steps <= 100_000 or not math.isfinite(beta) or not 0 <= beta <= 100:
        msg = "steps deve estar em 1..100000 e beta em 0..100."
        raise ValueError(msg)
    current = dict(case.assignment)
    if not evaluate(case.constraints, current):
        msg = "A cadeia deve começar num conjunto fático admissível."
        raise ValueError(msg)
    ids = [atom.id for atom in case.atoms]
    rng = random.Random(seed)
    score = disagreement(predict(dict(current)))
    trace = [{"step": 0, "assignment": dict(current), "difficulty": score, "accepted": True}]
    for step in range(1, steps + 1):
        proposal = dict(current)
        if rng.random() < 0.1:
            # Symmetric global jumps can connect disconnected admissible regions.
            proposal = {atom: bool(rng.getrandbits(1)) for atom in ids}
        else:
            atom = rng.choice(ids)
            proposal[atom] = not proposal[atom]
        admissible = evaluate(case.constraints, proposal)
        accepted = False
        if admissible:
            proposed_score = disagreement(predict(dict(proposal)))
            accepted = rng.random() < math.exp(min(0.0, beta * (proposed_score - score)))
            if accepted:
                current, score = proposal, proposed_score
        # Rejections are self-loops, including invalid proposals. Do not redraw.
        trace.append(
            {
                "step": step,
                "assignment": dict(current),
                "difficulty": score,
                "accepted": accepted,
                "proposal_admissible": admissible,
            }
        )
    return trace


# Imported measurements stay separate from the hidden formal reference.


class Predictions(Record):
    case_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    demonstration: bool
    models: list[Identifier] = Field(min_length=2)
    values: dict[str, list[UnitScore]]

    @model_validator(mode="after")
    def dimensions(self) -> Predictions:
        if len(set(self.models)) != len(self.models):
            msg = "Identidades de modelos devem ser distintas."
            raise ValueError(msg)
        if any(len(row) != len(self.models) for row in self.values.values()):
            msg = "Cada configuração exige uma previsão por modelo."
            raise ValueError(msg)
        return self

    def predictor(self, case: FormalCase) -> Callable[[dict[str, bool]], list[float]]:
        if case_digest(case) != self.case_sha256:
            msg = "Previsões pertencem a outro caso formal."
            raise ValueError(msg)
        ids = [atom.id for atom in case.atoms]
        if any(len(key) != len(ids) or set(key) - {"0", "1"} for key in self.values):
            msg = "Chaves devem ser vetores binários na ordem de atoms."
            raise ValueError(msg)

        def predict(assignment: dict[str, bool]) -> list[float]:
            key = "".join("1" if assignment[atom] else "0" for atom in ids)
            if key not in self.values:
                msg = "Configuração sem previsões: avalie os modelos antes de explorar."
                raise ValueError(msg)
            return self.values[key]

        return predict
