---
goal: "Remove src/djen_backup/inventory.py (ZipInventory + zip-inventory.txt IA helpers), a legacy (tribunal,date)->status tracker explicitly superseded by djen_backup/manifest.py's SyncManifest ('Replaces both ZipInventory and SyncState')."
id: "run-goals/20260907t092501z-fa-a-o-melhor-avan-o-poss-vel-n/goal-remove-dead-inventory-module"
kind: "task-advance"
rationale: "No open GitHub issue was actionable this round (all 17 open issues remain blocked per knowledge/backlog/, freshly re-verified 2026-09-07T02:45Z by run 7gg7l1) and there was no open PR to resume (wisk handoff list returned []). Per CLAUDE.md's own architecture section, sync-manifest.parquet/SyncManifest is meant to be the single source of truth; a second, fully unreferenced (tribunal,date)->status mechanism with its own on-IA file (zip-inventory.txt) sitting at 0% test coverage is exactly the kind of dual-source-of-truth confusion the project explicitly wants to avoid. Coverage sweep (uv run pytest --cov=src) confirmed inventory.py: 175/175 statements uncovered (0%), and a repo-wide grep confirmed zero imports of djen_backup.inventory or any of its symbols anywhere in src/, scripts/, tests/, or .github/ workflows."
run: "runs/20260907T092501Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
status: "achieved"
success_signal: "A new characterization test (tests/djen_backup/test_no_legacy_inventory_module.py) fails RED against the pre-existing tree (ModuleNotFoundError not raised, since the module exists) and passes GREEN after src/djen_backup/inventory.py is deleted; the full pytest -q suite, ruff check, and ruff format --check all stay green with the file removed, proving nothing else in the tree depended on it."
type: "RunGoal"
---

# RunGoal
