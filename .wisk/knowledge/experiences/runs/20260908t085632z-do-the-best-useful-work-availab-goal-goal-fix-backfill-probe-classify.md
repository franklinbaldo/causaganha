---
goal: "scripts/backfill_probe.py's local _classify(djen_raw) must bucket 'no_publications' (and any future absent sentinel) as 'absent', matching djen_backup.manifest.ABSENT_CODES, instead of falling through to a separate 'other:no_publications' bucket."
id: "run-goals/20260908t085632z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classify"
kind: "task-advance"
rationale: "This diagnostic script's whole purpose is to catch drift between the manifest's recorded djen_raw and a live re-probe (its own docstring: 'Spot rows where the manifest's recorded status disagrees with what the DJEN proxy returns right now'), but its local _classify hardcodes {'404','400'} for absent instead of importing the canonical ABSENT_CODES set from djen_backup.manifest -- so it never learned about the 'no_publications' sentinel engine.py (and, as of PR #1315, drain_unknowns.py) already write to the manifest for DJEN's 200-Sem-comunicacoes response. Every no_publications row gets miscategorized as 'other:no_publications' in the breakdown report, and _diff_label falsely reports 'DRIFT' for every such row it samples (manifest classifies as other:no_publications, the live re-probe's own bare status-code capture classifies the same live 200-Sem-comunicacoes response as available) even when the two are actually consistent -- exactly the class of duplicated-logic drift this session's own wiki note just documented for PR #1315."
run: "runs/20260908T085632Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/test_backfill_probe_classify.py asserts _classify('no_publications') == 'absent' (RED today), _classify('200')=='available', _classify('404')=='absent', _classify('403')=='rate-limited', _classify('timeout')=='transient', _classify('')=='unknown' all stay green after the fix, which replaces the hardcoded {'404','400'} literal with djen_backup.manifest.ABSENT_CODES; full repo suite/ruff stay green."
type: "RunGoal"
---

# RunGoal
