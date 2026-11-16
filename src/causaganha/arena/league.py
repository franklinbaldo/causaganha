"""Deterministic replay, earned eligibility and scarce judicial seats."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import mean

from causaganha.arena.models import Disposition, Level, Match, Rules, Season

PARENT = {
    Level.JUIZO: Level.ADVOCACIA,
    Level.TRIBUNAL: Level.JUIZO,
    Level.STJ: Level.TRIBUNAL,
    Level.STF: Level.TRIBUNAL,
}
WEIGHTS = dict(zip(Level, (1, 2, 4, 8, 8), strict=True))


def agreement(left: Disposition, right: Disposition) -> float:
    """Procedural dismissal is distinct from any merits outcome."""
    if left.merits != right.merits:
        return 0.0
    if not left.merits:
        return 1.0
    return 1 - abs(left.claimant_share - right.claimant_share)


def majority(match: Match, index: int) -> Disposition:
    votes = match.panels[index].votes
    counts = Counter((v.disposition.merits, v.disposition.claimant_share) for v in votes)
    (merits, share), count = counts.most_common(1)[0]
    if count <= len(votes) / 2:
        msg = "Colegiado sem maioria absoluta de dispositivo; registrar desempate antes do replay."
        raise ValueError(msg)
    return Disposition(merits=merits, claimant_share=share)


@dataclass
class League:
    rules: Rules
    competitors: list[str]
    scores: dict = field(default_factory=lambda: defaultdict(dict))
    # Qualification is earned once; seats are contested again every round.
    qualifications: dict = field(default_factory=dict)

    def average(self, competitor: str, level: Level) -> float:
        values = self.scores.get((competitor, level), {}).values()
        return mean(values) if values else 0.0

    def seats(self) -> dict[Level, list[str]]:
        limits = {
            Level.JUIZO: len(self.competitors),
            Level.TRIBUNAL: self.rules.court_seats,
            Level.STJ: self.rules.stj_seats,
            Level.STF: self.rules.stf_seats,
        }
        result = {Level.ADVOCACIA: sorted(self.competitors)}
        for level, parent in PARENT.items():
            candidates = [c for c in self.competitors if level in self.qualifications[c]]
            # Entry depends on the previous level; incumbency grants no ranking bonus.
            candidates.sort(key=lambda c: (-self.average(c, parent), -self.average(c, level), c))
            result[level] = candidates[: limits[level]]
        return result

    def qualify(self) -> None:
        for competitor in self.competitors:
            previous = set(self.qualifications[competitor])
            for level, parent in PARENT.items():
                samples = self.scores.get((competitor, parent), {})
                if (
                    parent in previous
                    and len(samples) >= self.rules.min_cases
                    and self.average(competitor, parent) >= self.rules.promotion_score
                ):
                    self.qualifications[competitor].add(level)

    def record(self, competitor: str, level: Level, case_id: str, score: float) -> None:
        samples = self.scores[competitor, level]
        if case_id in samples:
            msg = "Mesmo caso não pode pontuar novamente para competidor/papel."
            raise ValueError(msg)
        samples[case_id] = score

    def play(self, match: Match, seats: dict[Level, list[str]]) -> None:
        parties = [match.claimant.competitor, match.defendant.competitor]
        judges = [vote.competitor for panel in match.panels for vote in panel.votes]
        participants = parties + judges
        if len(participants) != len(set(participants)):
            msg = "Um competidor não pode ocupar dois papéis no mesmo processo."
            raise ValueError(msg)
        if not set(participants) <= set(self.competitors):
            msg = "Participante não cadastrado."
            raise ValueError(msg)
        levels = [panel.level for panel in match.panels]
        expected = [Level.JUIZO, Level.TRIBUNAL, match.anchor.court]
        if levels != expected[: len(levels)]:
            msg = "Instâncias devem seguir juizo → tribunal → corte da âncora."
            raise ValueError(msg)
        for panel in match.panels:
            if any(vote.competitor not in seats[panel.level] for vote in panel.votes):
                msg = "Julgador sem habilitação ou fora das vagas desta rodada."
                raise ValueError(msg)
        outcomes = [majority(match, i) for i in range(len(match.panels))]
        outcomes.append(match.anchor.disposition)
        # Bootstrap has no model-judge: only the real superior-court anchor scores advocacy.
        # A procedural dismissal gives no evidence about substantive advocacy success.
        merits = [outcome.claimant_share for outcome in outcomes if outcome.merits]
        if match.anchor.disposition.merits:
            sustained = mean(merits)
            for competitor, score in zip(parties, (sustained, 1 - sustained), strict=True):
                self.record(competitor, Level.ADVOCACIA, match.case_id, score)
        for index, panel in enumerate(match.panels):
            for vote in panel.votes:
                # A dissent scores against the NEXT instance, not its own majority.
                score = agreement(vote.disposition, outcomes[index + 1])
                self.record(vote.competitor, panel.level, match.case_id, score)

    def report(self) -> dict:
        seats = self.seats()
        rows = []
        for competitor in sorted(self.competitors):
            roles = {}
            reward = 0.0
            for level in Level:
                samples = self.scores.get((competitor, level), {})
                reward += sum(samples.values()) * WEIGHTS[level]
                roles[level] = {
                    "cases": len(samples),
                    "score": self.average(competitor, level) if samples else None,
                    "qualified": level in self.qualifications[competitor],
                    "seat": competitor in seats[level],
                }
            rows.append({"competitor": competitor, "reward": reward, "roles": roles})
        return {"standings": rows, "seats": seats}


def replay(season: Season) -> dict:
    league = League(season.rules, [entry.id for entry in season.competitors])
    league.qualifications = {c: {Level.ADVOCACIA} for c in league.competitors}
    history = []
    for round_ in season.rounds:
        seats = league.seats()
        for match in round_.matches:
            league.play(match, seats)
        league.qualify()
        history.append({"round": round_.id, "seats": league.seats()})
    return {
        "schema_version": 1,
        "demonstration": season.demonstration,
        "rules": season.rules.model_dump(mode="json"),
        "competitors": [entry.model_dump(mode="json") for entry in season.competitors],
        "history": history,
        **league.report(),
    }
