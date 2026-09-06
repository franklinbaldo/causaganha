---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-3-3-dead-code-gone"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
kind: "other"
reference: "repo tree at commit 652d404 — `find scripts/db deployment/cron deployment/systemd notebooks/train_privacy_filter.*` and `find . -iname AUDIT.md`"
summary: "#924 §3.3 named five dead-code targets. Live check: scripts/db/, deployment/cron/, deployment/systemd/, and notebooks/train_privacy_filter.* no longer exist in the tree (find reports 'No such file or directory' for all four — removed by earlier rounds, e.g. the fnt3vx round's experiments/archive/ cleanup and prior sessions). AUDIT.md was moved to docs/history/AUDIT.md with an explicit archival disclaimer added 2026-09-02 that cites this exact issue and sub-item ('Archived 2026-09-02, per issue #924 §3.3'). All five named targets are resolved exactly as the issue suggested."
---

# Evidência — #924 §3.3 (restos mortais) já purgados

Os cinco alvos citados (scripts/db, deployment/cron, deployment/systemd, notebooks de taxonomia v5, AUDIT.md) já não existem ou já foram movidos com aviso, conforme pedido pela própria issue.
