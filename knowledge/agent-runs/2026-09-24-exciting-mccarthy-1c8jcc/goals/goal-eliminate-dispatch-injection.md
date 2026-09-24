---
type: AgentGoal
id: "2026-09-24-exciting-mccarthy-1c8jcc-goal-eliminate-dispatch-injection"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
goal: "Eliminar a injecao de comando via workflow_dispatch (issue #1608, TM-01) em todos os workflows do GitHub Actions que constroem comandos de shell a partir de inputs de dispatch: nenhum valor de workflow_dispatch.inputs pode ser interpolado diretamente no corpo de um script 'run:' nem reinterpretado via 'eval'; inputs devem chegar como variaveis de ambiente e ser validados contra formato fechado antes de compor um comando com array Bash."
rationale: ".github/workflows/tjro-sync.yml (job com IA_ACCESS_KEY/IA_SECRET_KEY/RELAY_TOKEN no ambiente) monta uma string CMD a partir de tjro_ano/tjro_mes/tjro_desde_ano/tjro_tipos interpolados como ${{ inputs.X }} diretamente no texto do script e depois roda 'eval \"$CMD\"'. Uma demonstracao ao vivo nesta rodada (evidence-red-workflow-injection-demo) confirmou que isso e explorável mesmo sem o eval: a substituicao ${{ }} acontece como texto literal antes do bash processar o script, entao um valor malicioso de tjro_mes contendo ';' executa comandos arbitrarios no runner secret-bearing. A propria issue #1608 pede para auditar os demais workflows com o mesmo padrao; a auditoria desta rodada encontrou 5 arquivos adicionais com a mesma classe de vulnerabilidade: .github/workflows/datajud-enrich.yml (eval explicito, mesmas credenciais IA), .github/workflows/bootstrap-corpus.yml e .github/workflows/collect-zips.yml (interpolacao direta sem eval, mesmas credenciais IA, collect-zips.yml roda a cada 20 minutos), .github/workflows/roundtrip-check.yml e .github/workflows/sample-segmenter-texts.yml (interpolacao direta sem eval, sem secrets no job, mas ainda executando texto controlado pelo dispatcher no runner). Corrigir apenas tjro-sync.yml deixaria o mesmo padrao aberto em 5 outros lugares, violando o proprio criterio de conclusao da issue ('busca nos demais workflows nao encontra padrao equivalente sem justificativa explicita')."
success_signal: "Um novo teste de regressao (tests/test_workflow_dispatch_injection.py) prova, executando o script real extraido de cada um dos 6 workflows via subprocess bash com um stub de 'uv' no PATH, que: (1) nenhum dos 6 arquivos contem mais 'eval' nem uma expressao ${{ inputs.* }}/${{ github.event.inputs.* }} dentro do corpo de um script run: vulneravel (assercao estatica via yaml.safe_load); (2) valores maliciosos contendo ';', '$()', crase ou newline em cada input de dispatch sao rejeitados (exit != 0, nenhuma chamada ao stub 'uv') pela validacao de formato fechado; (3) valores validos geram exatamente a sequencia de argumentos esperada no stub. O teste falha (RED) contra o conteudo atual dos workflows antes da correcao e passa (GREEN) depois. uv run ruff check/format --check e uv run pytest -q ficam verdes; o comportamento de cron/backfill de cada workflow permanece inalterado (mesmos defaults quando o input esta vazio)."
status: "achieved"
---

# Objetivo: eliminar injecao de comando via workflow_dispatch (#1608, TM-01)

Trabalho principal desta rodada, proximo item na ordem de execucao do
threat model apos `#1612`/TM-09 (fechada pela rodada anterior) e
`#1615`/TM-07 (fechada por uma rodada Wisk concorrente, mesclada nesta
rodada). Ver `decision_ids`/`evidence_ids`/`check_ids` para o processo
TDD completo.
