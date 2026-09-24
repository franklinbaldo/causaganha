---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-1c8jcc-decision-fix-all-six-workflows"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
question: "#1608 cita apenas .github/workflows/tjro-sync.yml no corpo, mas pede para 'auditar os demais workflows que montam comandos a partir de workflow_dispatch.inputs'. A auditoria encontrou o mesmo padrao (interpolacao direta ${{ inputs.X }} no corpo de um run:, com ou sem eval subsequente) em mais 5 arquivos. Corrigir so tjro-sync.yml ou os 6?"
choice: "Corrigir os 6: tjro-sync.yml, datajud-enrich.yml (eval explicito, mesma credencial IA), bootstrap-corpus.yml e collect-zips.yml (interpolacao direta sem eval, mesma credencial IA), roundtrip-check.yml e sample-segmenter-texts.yml (interpolacao direta sem eval, sem secrets no job)."
rationale: "O criterio de conclusao da propria issue #1608 e explicito: 'busca nos demais workflows nao encontra padrao equivalente sem justificativa explicita'. Uma demonstracao ao vivo (evidence-red-workflow-injection-demo) provou que a vulnerabilidade real e a interpolacao ${{ inputs.X }} dentro do texto do script run: -- o 'eval' citado no titulo da issue e um segundo estagio da mesma familia de bug, nao a causa raiz. Deixar datajud-enrich.yml (mesmo eval, mesmas credenciais IA) ou bootstrap-corpus.yml/collect-zips.yml (mesma interpolacao insegura, mesmas credenciais IA, collect-zips.yml roda a cada 20 minutos) sem correcao seria fechar #1608 com o padrao equivalente ainda presente e sem nenhuma justificativa explicita registrada -- o que a issue proibe. roundtrip-check.yml/sample-segmenter-texts.yml nao tem secrets no job, mas o mesmo texto controlado pelo dispatcher ainda vira codigo de shell executado no runner (GITHUB_TOKEN de leitura, acesso a rede), entao o mesmo invariante ('nenhum valor de workflow_dispatch pode virar codigo de shell') se aplica igualmente; o custo marginal de corrigi-los na mesma mudanca (mesmo padrao de fix, mesma bateria de testes) e baixo comparado a deixar uma vulnerabilidade documentada e nao corrigida no repositorio."
---

# Decisao: escopo da correcao inclui os 6 workflows com o padrao

Ver `goal-eliminate-dispatch-injection` para o objetivo completo e
`evidence-red-workflow-injection-demo` para a prova de exploracao ao
vivo que motivou expandir o escopo alem do arquivo citado no titulo
da issue.
