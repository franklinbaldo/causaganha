---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-1c8jcc-evidence-red-pytest"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
kind: "test_red"
reference: "tests/test_workflow_dispatch_injection.py (49 casos) contra o conteudo pre-fix dos 6 workflows"
summary: "tests/test_workflow_dispatch_injection.py foi escrito primeiro contra a correcao ja planejada (nomes de env var, argv esperado). Antes de aplicar a correcao aos arquivos .yml, usado 'git stash' para reverter temporariamente os 6 workflows ao conteudo original (com eval/interpolacao direta) e rodado o teste: 30 dos 49 casos falharam -- as assercoes estaticas (sem eval, sem '${{ inputs' no corpo do run:) falham porque o padrao ainda esta la; as assercoes dinamicas (input malicioso rejeitado, input valido gera argv exato) falham porque o script pre-fix nao le nenhuma das variaveis de ambiente que o teste passa (TJRO_ANO, DATAJUD_TRIBUNAL_INPUT, etc. nao existem ainda), entao ou o bash da erro de sintaxe em '${{ ... }}' (nao processado fora do runtime real do GitHub Actions) ou o comando roda com argumentos vazios/errados. 'git stash pop' restaurou a correcao logo em seguida, sem deixar o repositorio no estado pre-fix commitado em nenhum momento."
---

# Evidencia: teste RED contra os workflows antes da correcao

```
$ git stash push -- .github/workflows/tjro-sync.yml .github/workflows/datajud-enrich.yml \
    .github/workflows/bootstrap-corpus.yml .github/workflows/collect-zips.yml \
    .github/workflows/roundtrip-check.yml .github/workflows/sample-segmenter-texts.yml
Saved working directory and index state WIP on claude/exciting-mccarthy-1c8jcc: 111dad0 ...

$ uv run pytest -q tests/test_workflow_dispatch_injection.py
FAILED tests/test_workflow_dispatch_injection.py::test_tjro_sync_rejects_metacharacter_payloads[...]
FAILED tests/test_workflow_dispatch_injection.py::test_tjro_sync_rejects_unknown_tipo
FAILED tests/test_workflow_dispatch_injection.py::test_tjro_sync_valid_dispatch_inputs_produce_expected_argv
FAILED tests/test_workflow_dispatch_injection.py::test_tjro_sync_cron_defaults_to_full_backfill
FAILED tests/test_workflow_dispatch_injection.py::test_datajud_enrich_has_no_eval_or_spliced_inputs
FAILED tests/test_workflow_dispatch_injection.py::test_datajud_enrich_rejects_malicious_inputs[...] (4x)
FAILED tests/test_workflow_dispatch_injection.py::test_datajud_enrich_skip_upload_appends_flag
FAILED tests/test_workflow_dispatch_injection.py::test_bootstrap_corpus_has_no_spliced_inputs[...] (2x)
FAILED tests/test_workflow_dispatch_injection.py::test_bootstrap_corpus_download_rejects_non_integer
FAILED tests/test_workflow_dispatch_injection.py::test_bootstrap_corpus_download_valid_inputs_produce_expected_argv
FAILED tests/test_workflow_dispatch_injection.py::test_bootstrap_corpus_stage1_valid_input_produces_expected_argv
FAILED tests/test_workflow_dispatch_injection.py::test_collect_zips_has_no_eval_or_spliced_inputs
FAILED tests/test_workflow_dispatch_injection.py::test_collect_zips_rejects_malicious_inputs[...] (4x)
FAILED tests/test_workflow_dispatch_injection.py::test_collect_zips_valid_inputs_produce_expected_argv
FAILED tests/test_workflow_dispatch_injection.py::test_collect_zips_tribunal_and_end_date_append_flags
FAILED tests/test_workflow_dispatch_injection.py::test_roundtrip_check_has_no_spliced_inputs
FAILED tests/test_workflow_dispatch_injection.py::test_roundtrip_check_rejects_malicious_inputs[...] (2x)
FAILED tests/test_workflow_dispatch_injection.py::test_roundtrip_check_valid_inputs_produce_expected_argv
FAILED tests/test_workflow_dispatch_injection.py::test_sample_segmenter_texts_has_no_spliced_dispatch_inputs
FAILED tests/test_workflow_dispatch_injection.py::test_sample_segmenter_texts_valid_inputs_produce_expected_argv
30 failed, 19 passed

$ git stash pop
Dropped refs/stash@{0} (13553daf...)
```

30 de 49 casos falharam contra o conteudo original dos 6 workflows,
confirmando que a correcao planejada e realmente necessaria e que o
teste discrimina corretamente entre o codigo antigo (vulneravel) e o
novo. Os 19 casos que passaram mesmo sem a correcao sao os que nao
dependiam do padrao especifico sendo corrigido nesse arquivo (ex.:
`test_tjro_sync_rejects_metacharacter_payloads` para o campo
`TJRO_TIPOS`, que ja falhava fechado no script antigo por um motivo
diferente -- ausencia total da variavel).
