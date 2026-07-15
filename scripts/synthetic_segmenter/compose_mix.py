"""Static training-mix composition — the real integration point (RFC 0011 §15-bis.3).

``opf train`` accepts a path/glob of JSON/JSONL as its dataset argument
(verified against ``opf/_train/args.py``), but only as an **equal-weight
concatenated pool** — there is no per-source ratio/weight flag in the
parser. The ``TrainingMix`` weights from RFC 0011 §13 (e.g. "4x pristine
real per 1x synthetic") are therefore a **composition step that runs
before** ``opf train``, materializing a single ``train.jsonl`` with the
desired mixture already baked in by repetition/subsampling — exactly how
the pipeline already produces today's single pristine ``train.jsonl``.

**Scope, precisely** (RFC 0011 §15-bis.3): this covers Runs C/E/F/G — a
single static mix, a single ``opf train`` call, no driver changes needed.
It does **not** cover Runs B/D (staged curricula — pretrain-then-finetune,
adversarial-then-real-heavy), which need a new multi-call orchestrator
(``run_staged_training.py``, not built here) chaining ``opf train
--checkpoint`` across stages, each with its own ``compose_mix`` call.
That orchestrator, and the small ``opf_shared.build_opf_train_cmd``/
``train_and_eval`` change to expose ``--checkpoint``, are out of this
RFC's scope — this module only produces one mix for one training call.

``val.jsonl``/``test.jsonl`` never pass through this module, by
construction: it has no parameter for them and no code path that could
touch them. Callers build ``pools`` from train-only sources (RFC 0011
§10) — this module trusts that boundary the same way ``corpus_stats.py``
and ``hybrid.py`` do, it does not re-derive it from doc IDs it never sees.
"""

from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _draw(pool: list[dict], target_count: int, rng: random.Random) -> list[dict]:
    """Sample ``target_count`` records from ``pool``, deterministic in ``rng``.

    Without-replacement subsampling when the pool is large enough;
    with-replacement oversampling (every pool record used at least once,
    then filled by resampling) when the target exceeds the pool size —
    the "repetição" half of RFC 0011 §15-bis.3's "por repetição/amostragem".
    """
    if target_count <= 0 or not pool:
        return []
    if target_count <= len(pool):
        return rng.sample(pool, target_count)
    full_copies, remainder = divmod(target_count, len(pool))
    drawn = list(pool) * full_copies
    drawn.extend(rng.sample(pool, remainder))
    return drawn


def compose_mix(
    pools: dict[str, list[dict]],
    weights: dict[str, float],
    *,
    seed: int,
    mix_id: str,
    corpus_release_ids: Sequence[str],
    target_total: int | None = None,
    curriculum_stage: str | None = None,
) -> tuple[list[dict], dict]:
    """Compose one static training mix. Returns ``(records, manifest)``.

    ``pools`` maps source_type -> records already restricted to train
    (e.g. ``{"pristine_real": [...], "synthetic": [...]}``). ``weights``
    maps the same keys to relative proportions (need not sum to 1) — a
    source_type present in ``weights`` but absent from ``pools`` is
    treated as an empty pool, not an error (a mix can legitimately ask
    for a source that just hasn't been generated yet, e.g. mid-Phase-2
    rollout); a source_type present in ``pools`` but absent from
    ``weights`` is excluded from the mix entirely (weights are the
    authoritative selector).

    ``target_total`` defaults to the sum of every listed pool's size —
    the mix ends up roughly the size of everything available, redistributed
    by weight, rather than an arbitrary fixed count.

    Records are shuffled together (not grouped by source) so downstream
    consumers see the mixed order the training run will actually use.
    """
    total_weight = sum(weights.values())
    if total_weight <= 0:
        msg = f"weights must sum to a positive number, got {weights!r}"
        raise ValueError(msg)

    if target_total is None:
        target_total = sum(len(pools.get(source, [])) for source in weights)

    rng = random.Random(seed)
    composed: list[dict] = []
    counts_by_source_type: dict[str, int] = {}
    for source_type, weight in weights.items():
        pool = pools.get(source_type, [])
        target_count = round(target_total * weight / total_weight)
        drawn = _draw(pool, target_count, rng)
        composed.extend(drawn)
        counts_by_source_type[source_type] = len(drawn)

    rng.shuffle(composed)

    source_doc_ids_pristine_real = sorted(
        {
            record["info"]["doc_id"]
            for record in pools.get("pristine_real", [])
            if "doc_id" in record.get("info", {})
        }
    )

    manifest = {
        "mix_id": mix_id,
        "corpus_release_ids": list(corpus_release_ids),
        "weights": dict(weights),
        "counts_by_source_type": counts_by_source_type,
        "total_records": len(composed),
        "source_doc_ids_pristine_real": source_doc_ids_pristine_real,
        "seed": seed,
    }
    if curriculum_stage is not None:
        manifest["curriculum_stage"] = curriculum_stage

    return composed, manifest


def write_mix(
    records: list[dict], manifest: dict, *, output_path: Path, manifest_path: Path
) -> None:
    """Write the composed ``train.jsonl`` and its mix manifest to disk.

    Two separate files, deliberately: the mix manifest (this function's
    ``manifest``) is not the per-document provenance manifest of RFC 0011
    §15 — do not conflate the two when wiring this into a pipeline.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
