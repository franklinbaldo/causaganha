---
type: "RunReading"
id: "run-readings/20260909t004503z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260909T004503Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "This round's own prior Experience run (runs/20260909T002535Z) that produced PR #1350"
reference: ".wisk/knowledge/experiences/runs/20260909t002535z-*.md"
finding: "That run found and fixed two bugs in src/causaganha/consolidate/cli.py: (1) reconsolidate()'s --force option called typer.Option(\"--force\", default=False, ...), colliding with Typer's own positional 'default' parameter and crashing the entire module at import time -- undetected because no test imported the module; (2) _uploads_complete() gated the dry-run manifest write on an upload count that dry-run mode can never produce, silently skipping manifest registration for real, non-empty dry-run consolidations. Both fixed via TDD, merged as PR #1350 (squash ed0973c)."
---

# RunReading
