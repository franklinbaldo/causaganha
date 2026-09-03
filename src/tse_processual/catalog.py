"""Authoritative catalog for the first TSE Processual 2026 proof slice."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResourceKind(StrEnum):
    """Resources intentionally admitted into the initial proof."""

    PROCESSOS = "processos"
    ASSUNTOS = "assuntos"
    DECISOES = "decisoes"


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """One official Processual resource and the public URL observed in the TSE catalog."""

    kind: ResourceKind
    year: int
    url: str


PROCESSUAL_2026_RESOURCES = (
    ResourceSpec(kind=ResourceKind.PROCESSOS, year=2026, url="https://cdn.tse.jus.br/estatistica/sead/odsele/processual/processo_eleitoral_2026.zip"),
    ResourceSpec(kind=ResourceKind.ASSUNTOS, year=2026, url="https://cdn.tse.jus.br/estatistica/sead/odsele/processual/processos_eleitorais_assuntos_2026.zip"),
    ResourceSpec(kind=ResourceKind.DECISOES, year=2026, url="https://cdn.tse.jus.br/estatistica/sead/odsele/processual/processos_eleitorais_decisoes_2026.zip"),
)


def resource_for(kind: ResourceKind, *, year: int = 2026) -> ResourceSpec:
    """Return the admitted official resource, rejecting unsupported years/kinds explicitly."""
    for resource in PROCESSUAL_2026_RESOURCES:
        if resource.kind is kind and resource.year == year:
            return resource
    msg = f"TSE Processual resource not admitted: kind={kind.value}, year={year}"
    raise ValueError(msg)
