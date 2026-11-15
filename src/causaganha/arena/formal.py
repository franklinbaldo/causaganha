"""Finite synthetic cases, kernel-checkable certificates and narrative provenance.

This restricted propositional language is a starting point, not a formalization
of Brazilian law. No user-supplied Lean code is evaluated.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from pydantic import Field, model_validator

from causaganha.arena.models import Identifier, Record

AtomId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class Atom(Record):
    id: AtomId
    statement: Identifier


class Literal(Record):
    atom: AtomId
    positive: bool = True


class FormalCase(Record):
    id: Identifier
    question: Identifier
    # Explicit synthetic boundary; reconstructed real cases need a different contract.
    synthetic: bool = True
    atoms: list[Atom] = Field(min_length=1, max_length=64)
    assignment: dict[str, bool]
    # CNF: AND of OR clauses. Empty clause is false; empty formula is true.
    constraints: list[list[Literal]] = Field(default_factory=list)
    claim: list[list[Literal]] = Field(min_length=1)

    @model_validator(mode="after")
    def references(self) -> FormalCase:
        ids = [atom.id for atom in self.atoms]
        if not self.synthetic:
            msg = "Este contrato é exclusivo de casos sintéticos."
            raise ValueError(msg)
        if len(ids) != len(set(ids)) or set(ids) != set(self.assignment):
            msg = "Átomos únicos e uma atribuição completa são obrigatórios."
            raise ValueError(msg)
        if any(lit.atom not in ids for clause in self.constraints + self.claim for lit in clause):
            msg = "Literal referencia átomo desconhecido."
            raise ValueError(msg)
        return self


def evaluate(clauses: list[list[Literal]], assignment: dict[str, bool]) -> bool:
    return all(any(assignment[lit.atom] == lit.positive for lit in clause) for clause in clauses)


def case_digest(case: FormalCase) -> str:
    canonical = json.dumps(case.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def lean_source(case: FormalCase) -> str:
    """Export only a controlled syntax; arbitrary text never enters Lean source."""
    names = {atom.id: f"fact{i}" for i, atom in enumerate(case.atoms)}

    def formula(clauses: list[list[Literal]]) -> str:
        parts = []
        for clause in clauses:
            terms = [f"({names[lit.atom]} = {str(lit.positive).lower()})" for lit in clause]
            parts.append("(" + " ∨ ".join(terms) + ")" if terms else "False")
        return " ∧ ".join(parts) if parts else "True"

    lines = ["-- Synthetic arena case SHA-256: " + case_digest(case), "namespace ArenaCase"]
    for atom in case.atoms:
        lines.append(f"def {names[atom.id]} : Bool := {str(case.assignment[atom.id]).lower()}")
    lines += [
        f"abbrev admissible : Prop := {formula(case.constraints)}",
        f"abbrev claim : Prop := {formula(case.claim)}",
        "theorem consistent : admissible := by decide",
        "theorem outcome : "
        + ("claim" if evaluate(case.claim, case.assignment) else "¬ claim")
        + " := by decide",
        "#print axioms consistent",
        "#print axioms outcome",
        "end ArenaCase",
    ]
    return "\n".join(lines) + "\n"


def verify(case: FormalCase, lean: str = "lean", timeout: int = 30) -> dict[str, str]:
    """Compile generated code and require an empty axiom dependency report."""
    source = lean_source(case)
    with tempfile.TemporaryDirectory(prefix="arena-lean-") as directory:
        path = Path(directory) / "Case.lean"
        path.write_text(source, encoding="utf-8")
        version = subprocess.run(
            [lean, "--version"], check=True, capture_output=True, text=True, timeout=timeout
        ).stdout.strip()
        result = subprocess.run(
            [lean, str(path)], check=True, capture_output=True, text=True, timeout=timeout
        )
    for theorem in ("consistent", "outcome"):
        if f"'ArenaCase.{theorem}' does not depend on any axioms" not in result.stdout:
            msg = "Certificado não comprovou dependências axiomáticas vazias."
            raise ValueError(msg)
    return {
        "case_sha256": case_digest(case),
        "lean_version": version,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "status": "verified",
        "axioms": result.stdout.strip(),
    }


def narrative_request(case: FormalCase) -> dict:
    """Public facts only: do not send the hidden outcome/certificate to a narrator."""
    return {
        "case_id": case.id,
        "case_sha256": case_digest(case),
        "synthetic": True,
        "question": case.question,
        "facts": [
            {"id": atom.id, "statement": atom.statement, "holds": case.assignment[atom.id]}
            for atom in case.atoms
        ],
        "instruction": "Redija autos fictícios. Preserve todos os fatos e suas polaridades; "
        "não acrescente fatos relevantes. Vincule cada trecho aos IDs correspondentes. "
        "Não antecipe uma decisão. A fidelidade semântica será revisada separadamente.",
    }


class NarrativeSegment(Record):
    text: Identifier
    fact_ids: list[AtomId] = Field(min_length=1)


class Narrative(Record):
    case_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    segments: list[NarrativeSegment] = Field(min_length=1)


def audit_narrative(case: FormalCase, narrative: Narrative) -> dict:
    if narrative.case_sha256 != case_digest(case):
        msg = "Narrativa pertence a outra versão dos fatos."
        raise ValueError(msg)
    expected = {atom.id for atom in case.atoms}
    covered = {item for segment in narrative.segments for item in segment.fact_ids}
    if expected != covered:
        msg = "Narrativa deve referenciar todos os fatos, sem IDs desconhecidos."
        raise ValueError(msg)
    return {
        "case_sha256": case_digest(case),
        "coverage": "complete",
        "semantic_fidelity": "unverified",
        "ready_for_benchmark": False,
    }
