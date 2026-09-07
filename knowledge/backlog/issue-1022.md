---
type: BacklogItem
issue_number: 1022
title: "data(tcu): publicar Parquet TEOR 2026 no Internet Archive com prova de leitura"
category: "credentials"
blocking_reason: "Requires a live, credentialed upload to Internet Archive. This session's environment was checked (`env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE'`) and has no IAS3_ACCESS_KEY/IAS3_SECRET_KEY (the variables src/causaganha/pipeline/ia_s3.py reads); only unrelated AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are set, and the project explicitly does not use AWS-style auth for IA (CLAUDE.md: 'Don't use boto3 for IA uploads')."
unblock_condition: "A session whose environment has real IAS3_ACCESS_KEY/IAS3_SECRET_KEY set."
last_verified_run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
last_verified_at: "2026-09-07T02:45:00Z"
status: "blocked"
---

# Issue #1022: data(tcu): publicar Parquet TEOR 2026 no Internet Archive com prova de leitura

Requires a live, credentialed upload to Internet Archive. This session's environment was checked (`env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE'`) and has no IAS3_ACCESS_KEY/IAS3_SECRET_KEY (the variables src/causaganha/pipeline/ia_s3.py reads); only unrelated AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are set, and the project explicitly does not use AWS-style auth for IA (CLAUDE.md: 'Don't use boto3 for IA uploads').

**Para desbloquear:** A session whose environment has real IAS3_ACCESS_KEY/IAS3_SECRET_KEY set.
