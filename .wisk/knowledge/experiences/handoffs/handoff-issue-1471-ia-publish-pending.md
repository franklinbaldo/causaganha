---
created_at: "2026-09-15T00:43:40.157340Z"
created_by_run: "runs/20260915T002743Z-do-the-best-useful-work-available-in-this-reposi"
goals: []
id: "handoffs/handoff-issue-1471-ia-publish-pending"
next_action: "Once IA write credentials are available: (1) publish the candidate (numero_processo-reordered, layout_revision=2) comunicacoes.parquet as a pilot to djen-tjro-2026, preserving rollback -- keep the currently published file recoverable, do not delete/overwrite without a documented way back; (2) run scripts/benchmarks/pilot_tjro_2026_real_archive_readback.py's technique (already proven this round's predecessor handoff, real metadata/head-range/tail-range probes + native DuckDB cold/warm timing) against the newly published candidate for a true apples-to-apples real-Archive comparison against docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json's old-file baseline; (3) only after that read-back is validated, record issue #1471's advance/revise/hold decision with agreed regression limits, using PR #1480's local-simulation numbers and the old-file real numbers together as the baseline -- do not promote catalog/certification before that read-back is validated, per the issue's own text."
references: ["https://github.com/franklinbaldo/causaganha/issues/1471", "https://github.com/franklinbaldo/causaganha/issues/1472", "https://github.com/franklinbaldo/causaganha/pull/1480", "https://github.com/franklinbaldo/causaganha/pull/1483", "https://github.com/franklinbaldo/causaganha/pull/1489"]
repository_branch: "main"
repository_diff_digest: "sha256:030424b3e6409a188dcd23f6f9bfd389f4876ef8b455c27ad3ce2aae98f70a2f"
repository_dirty: "true"
repository_head: "37c0f14c576380f0969acd8f224e2a627618e2f9"
state: "handoffs/handoff-issue-1471-archive-readback-v2's item 3 (real-browser CORS confirmation for issue #1482) is done -- PR #1489, docs/planning/evidence/archive-cors-probe-real-browser.json. Items 1/2/4 remain exactly as before: no IA credentials found via any supported source (IAS3_ACCESS_KEY/IAS3_SECRET_KEY, IA_ACCESS_KEY/IA_SECRET_KEY, or ~/.config/internetarchive/ia.ini -- confirmed live against src/causaganha/pipeline/ia_s3.py's own get_ia_s3_auth() resolver, not just an env-var grep), so the reordered comunicacoes.parquet candidate for djen-tjro-2026 still cannot be published, no apples-to-apples real read-back against it exists, and issue #1471's advance/revise/hold decision cannot yet be recorded (it is gated on that read-back per the issue's own acceptance criteria). This is at least the eleventh consecutive round (since 2026-09-11) to reconfirm this exact same credential gap; a future round with IA write access should treat it as immediately actionable rather than re-diagnosing. `repository_head`/`repository_branch` corrected on 2026-09-20: the original ca795fbcc08d89ff717139687705b5ee803c987c (branch claude/exciting-mccarthy-vdj7ti) was PR #1489's pre-squash commit, discarded when GitHub squash-merged it as 37c0f14c576380f0969acd8f224e2a627618e2f9 on main -- it was never going to become reachable again, so 10+ prior rounds' 'baseline commit unreachable' finding was noise about a discarded intermediate commit, not a real blocker; the only real blocker is, and always was, the missing IA credentials."
status: "archived"
target_session_type: "session-types/standard-experience"
title: "Finish issue #1471's TJRO 2026 pilot: publish candidate to Internet Archive, real candidate read-back proof, advance/revise/hold decision"
type: "Handoff"
continued_by_run: "runs/20260925T140520Z-do-the-best-useful-work-available-in-this-reposi"
archived_at: "2026-09-25T14:09:10.509027Z"
resolution: "Reconfirmado ao vivo (12a rodada consecutiva desde 2026-09-11): credenciais de escrita IA continuam ausentes, mesmo estado exato das rodadas anteriores. Superseded por handoffs/handoff-issue-1471-ia-publish-pending-v3, que carrega a mesma condicao de reativacao e proxima acao (nenhuma mudanca de conteudo, so uma reconfirmacao datada e o goal formal desta rodada carried_forward)."
---

# Handoff
