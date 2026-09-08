"""Single source of truth for the absent/djen_raw self-consistency rule.

CLAUDE.md: ``djen_raw="200"`` is the transport code, not a verdict — a
``djen_status="absent"`` row with a bare ``200`` raw contradicts itself,
because ``interpret_djen_raw('200')`` would re-derive ``available``. And an
``absent`` row with no ``djen_raw`` at all can't be re-verified ("Don't
trust `absent` from old runs... reset all `absent` entries where `djen_raw`
is empty to unknown").

Two independent runtimes apply this same rule and had already drifted once
before being caught (PR #1323): ``SyncManifest._normalize_event``
(``src/djen_backup/manifest.py``, in-memory engine, one row at a time) and
``_normalize_manifest`` (``scripts/render_manifest_parquet.py``, DuckDB SQL,
bulk ``UPDATE`` over the whole table). A SQL ``UPDATE`` can't call a Python
function per row without giving up its bulk-set performance, so this module
is the constants + the Python-side predicate/transform both runtimes must
build from — the SQL literals below must be interpolated from these same
constants rather than re-typed.
"""

from __future__ import annotations


ABSENT = "absent"
NO_PUBLICATIONS_SENTINEL = "no_publications"
BARE_200_RAW = "200"
PREFIXED_200_RAW_PREFIX = "200:"


def is_contradictory_200(djen_status: str, djen_raw: str) -> bool:
    """True when an ``absent`` verdict carries a raw that would re-derive ``available``."""
    return djen_status == ABSENT and (
        djen_raw == BARE_200_RAW or djen_raw.startswith(PREFIXED_200_RAW_PREFIX)
    )


def is_unverifiable_absent(djen_status: str, djen_raw: str) -> bool:
    """True when an ``absent`` verdict has no raw code to re-derive it from."""
    return djen_status == ABSENT and not djen_raw


def normalize_absent(djen_status: str, djen_raw: str) -> tuple[str, str]:
    """Apply the absent self-consistency rule to one ``(djen_status, djen_raw)`` pair.

    Order matters: the contradictory-200 rewrite runs first so its sentinel
    output (a non-empty raw) never trips the unverifiable-absent downgrade.
    """
    if is_contradictory_200(djen_status, djen_raw):
        djen_raw = NO_PUBLICATIONS_SENTINEL
    if is_unverifiable_absent(djen_status, djen_raw):
        djen_status = ""
    return djen_status, djen_raw
