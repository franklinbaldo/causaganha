---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-1c8jcc-evidence-green-pytest"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
kind: "test_green"
reference: "tests/test_workflow_dispatch_injection.py (49 casos) apos a correcao aplicada aos 6 workflows"
summary: "Apos corrigir .github/workflows/{tjro-sync,datajud-enrich,bootstrap-corpus,collect-zips,roundtrip-check,sample-segmenter-texts}.yml (mover todo input de workflow_dispatch para env:, remover 'eval', substituir string+eval/execucao nao-quotada por array Bash + \"${CMD[@]}\", adicionar validacao de formato fechado), os 49 casos de tests/test_workflow_dispatch_injection.py passam: assercoes estaticas (nenhum dos 6 arquivos contem mais 'eval' nem uma expressao ${{ inputs.* }}/${{ github.event.inputs.* }} dentro do corpo de um script run: vulneravel), payloads maliciosos com ';', '$()', crase ou newline sao rejeitados (exit != 0, nenhuma chamada ao stub 'uv', nenhum arquivo 'pwned' criado) para cada input de dispatch dos 6 workflows, e inputs validos gera exatamente a sequencia de argumentos esperada -- incluindo o comportamento de default do cron de tjro-sync.yml (--desde-ano 1988 quando nenhum input e fornecido fora de workflow_dispatch), que permanece inalterado."
---

# Evidencia: teste GREEN apos a correcao

```
$ uv run pytest -q tests/test_workflow_dispatch_injection.py
...............................................                          [100%]
49 passed
```

Todos os 49 casos passam contra o conteudo real e atual dos 6
workflows corrigidos.
