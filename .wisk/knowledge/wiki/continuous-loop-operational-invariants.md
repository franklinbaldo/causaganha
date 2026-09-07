---
type: "WikiEntry"
id: "wiki/continuous-loop-operational-invariants"
title: "Continuous-loop operational invariants"
status: "active"
tags: ["wisk", "continuous-loop", "repository-maintenance", "handoffs"]
---

# Continuous-loop operational invariants

## Summary

The continuous CausaGanha loop is most reliable when Wisk owns orchestration and each session treats current repository/GitHub state as evidence rather than assuming that the issue backlog is the whole work queue. Recent Experience runs repeatedly found useful, bounded work after the open issue queue was blocked: a shipped CLI without tests exposed a real validation defect (#1265), an entirely unused legacy inventory implementation was removed (#1267), and a persistence defect in the Wisk bootstrap path was found and repaired (#1270/#1271).

Wisk state has one canonical repository namespace: `.wisk/`. Versionable Experience, Wiki, Skill and local consumer knowledge belong beneath `.wisk/knowledge/`. During the package rename, #1270/#1271 temporarily used a tracked `.wisk -> .wikiskill` symlink to prevent state loss; #1274 later migrated the entire historical tree into `.wisk/` and removed the old namespace. The symlink is therefore useful migration evidence, not a current invariant and not a pattern to recreate.

Cross-session PR continuation should remain explicit through Wisk handoffs. A run that leaves CI or merge work pending records a Handoff; the continuing session first reconstructs the factual repository/GitHub state, then acts on the still-valid remainder and archives the Handoff only after resolution. A stale handoff instruction is never stronger evidence than the repository state observed on resume.

## Context & Scope

These rules apply to unattended or periodically invoked CausaGanha work sessions. They do not authorize speculative features when current issues are blocked, nor do they turn coverage/dead-code scans into a mandatory ritual. They describe a proven fallback: prefer independently verifiable repository improvements over manufacturing work merely to keep the loop busy.

The issue backlog remains important context, but it is a queue of known opportunities rather than a completeness claim about all possible useful work. Before acting on cached blocker descriptions, refresh the relevant GitHub/environment facts when staleness could change the decision.

## Evidence & Lineage

- `../experiences/runs/20260907T082458Z-fa-a-o-melhor-avan-o-poss-vel-no-reposit-rio-fra.md`: no actionable PR/issue; coverage of the shipped `causaganha` CLI found and fixed a genuine output-validation inconsistency, delivered in #1265.
- `../experiences/runs/20260907T092501Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio.md`: coverage plus repository-reference scan proved `ZipInventory` was dead and superseded by `SyncManifest`, leading to #1267.
- `../experiences/runs/20260907T103000Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio.md`: direct execution proved Wisk was writing state into a separate ignored `.wisk/` path under the then-current split namespace; #1270 introduced the symlink compatibility repair.
- `../experiences/runs/20260907T104446Z-confirmar-merge-da-pr-1270-e-arquivar-o-handoff.md`: a subsequent run verified that temporary repair end to end before the namespace was later consolidated.
- PR #1274 / commit `66f145c45d52651eedddc99d10d0a25ed86df8b5`: migrated all historical Wisk state into `.wisk/`, removed `.wikiskill/`, and added regression guards for the canonical namespace.
