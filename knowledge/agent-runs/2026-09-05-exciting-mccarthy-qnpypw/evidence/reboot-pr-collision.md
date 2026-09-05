---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qnpypw-evidence-reboot-pr-collision"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1169 and https://github.com/franklinbaldo/causaganha/pull/1170"
summary: "Both PRs target issue #1168 (full web/ rebuild onto Panda CSS + Cobogó) against the same main head (aeb54a7), opened 5m35s apart by two different concurrent sessions. #1169: 22 files, +3341/-1711, rebuilds six surfaces; CI at read time: lint=failure, several jobs in_progress. #1170: 7 files, +2764/-500, narrower first-slice (shell+home only); CI at read time: tests(tjro)=failure, mergeable_state=behind. Neither is stale/abandoned. Flagged to the user via notification rather than resolved unilaterally (see AgentDecision avoid-web-reboot-collision)."
---

# Evidência — colisão de PRs no reboot visual (#1168)

Registro objetivo do estado das duas PRs concorrentes no momento da leitura, para orientar a próxima rodada (ou o próprio usuário) sobre qual delas seguir, sem que esta rodada tenha decidido por elas.
