"""Deterministic fictional identities (RFC 0011 §7).

Anti-memorization / dataset-quality default for generated documents — not
a legal/PII requirement (docs/GOVERNANCE.md already covers reuse of public
judicial text; see RFC 0011 §7). Every value here is fully synthetic:
fictional party/lawyer/judge names, a CNJ-shaped but non-resolving process
number, a structurally-valid but non-checksummed OAB number.

Everything is derived from a single ``identity_seed`` so the same seed
always reproduces the same identity set (RFC 0011 §15 ``identity_seed``).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


_GIVEN_NAMES = (
    "Ana",
    "Bruno",
    "Carla",
    "Daniel",
    "Elisa",
    "Fábio",
    "Gabriela",
    "Hugo",
    "Isabela",
    "João",
    "Larissa",
    "Marcos",
    "Natália",
    "Otávio",
    "Paula",
    "Rafael",
    "Sofia",
    "Tiago",
)
_SURNAMES = (
    "Almeida",
    "Barbosa",
    "Carvalho",
    "Duarte",
    "Ferreira",
    "Gonçalves",
    "Henriques",
    "Lacerda",
    "Martins",
    "Nogueira",
    "Oliveira",
    "Pereira",
    "Queiroz",
    "Ribeiro",
    "Souza",
    "Teixeira",
    "Vieira",
)
_COMPANY_SUFFIXES = (
    "Comércio de Materiais Ltda.",
    "Serviços Ltda.",
    "Indústria S.A.",
    "Transportes Ltda.",
)
_COMPANY_STEMS = ("Estrela", "Horizonte", "Cascata", "Vale Verde", "Nova Aurora", "Bandeirantes")


@dataclass(frozen=True)
class Identity:
    """One fictional person or company name."""

    full_name: str
    is_company: bool = False


@dataclass(frozen=True)
class IdentitySet:
    """One fictional identity set for a single generated document."""

    identity_seed: int
    autor: Identity
    reu: Identity
    advogado_autor: str
    advogado_reu: str
    juiz: str
    oab_autor: str
    oab_reu: str
    numero_processo: str


def _fictional_person(rng: random.Random) -> Identity:
    return Identity(full_name=f"{rng.choice(_GIVEN_NAMES)} {rng.choice(_SURNAMES)}")


def _fictional_company(rng: random.Random) -> Identity:
    name = f"{rng.choice(_COMPANY_STEMS)} {rng.choice(_COMPANY_SUFFIXES)}"
    return Identity(full_name=name, is_company=True)


def _fictional_oab(rng: random.Random) -> str:
    # Structurally OAB-shaped (digits + UF), never validated against a real registry.
    return f"OAB/{rng.choice(('RO', 'SP', 'MG', 'RJ'))} {rng.randint(1000, 99999)}"


def _fictional_process_number(rng: random.Random) -> str:
    # CNJ format: NNNNNNN-DD.AAAA.J.TR.OOOO — digits only, never a real process.
    sequencial = rng.randint(0, 9_999_999)
    dv = rng.randint(10, 99)
    ano = rng.randint(2015, 2026)
    tribunal = rng.choice(("8.22", "8.26", "8.13"))
    orgao = rng.randint(1, 9999)
    return f"{sequencial:07d}-{dv}.{ano}.{tribunal}.{orgao:04d}"


def generate_identities(identity_seed: int) -> IdentitySet:
    """Build one fully-fictional, internally-consistent identity set.

    Deterministic: the same ``identity_seed`` always returns byte-identical
    values (RFC 0011 §15 reproducibility requirement).
    """
    rng = random.Random(identity_seed)
    autor = _fictional_company(rng) if rng.random() < 0.3 else _fictional_person(rng)
    reu = _fictional_company(rng) if rng.random() < 0.3 else _fictional_person(rng)
    return IdentitySet(
        identity_seed=identity_seed,
        autor=autor,
        reu=reu,
        advogado_autor=_fictional_person(rng).full_name,
        advogado_reu=_fictional_person(rng).full_name,
        juiz=_fictional_person(rng).full_name,
        oab_autor=_fictional_oab(rng),
        oab_reu=_fictional_oab(rng),
        numero_processo=_fictional_process_number(rng),
    )
