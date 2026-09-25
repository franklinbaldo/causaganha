---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-e0vvbh-decision-scope-tm04-tribunal-only"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
goal_id: "2026-09-25-exciting-mccarthy-e0vvbh-goal-tribunal-coerente-manifesto"
question: "#1610/TM-04 pede coerência de tribunal/período/generation id/schema fingerprint/row count/hash. Implementar tudo nesta rodada, ou recortar uma fatia tratável em TDD self-contained?"
choice: "Implementar somente a coerência tribunal<->arquivo_ia_url para as fontes djen/datajud (cujo item IA é particionado por tribunal). Generation id/schema fingerprint/hash/row count ficam como follow-up explícito, pois exigem inventar campos novos no gerador do manifesto (reconcile_processos.py) que hoje não existem em lugar nenhum do código."
rationale: "Uma sub-agente de investigação (Explore) confirmou, com grep e leitura de reconcile_processos.py/service.py, que: (1) indice_processual.parquet já tem uma coluna `tribunal` por linha, escrita pelo mesmo gerador que escreve `arquivo_ia_url`, mas o service.py atual só seleciona `fonte, arquivo_ia_url` -- o cruzamento é uma mudança puramente aditiva dentro do módulo já responsável pela política de URL (#1622); (2) generation id, schema fingerprint, hash e row-count-do-parquet não existem em nenhum lugar do código (nem em reconcile_processos.py, nem no sistema irmão djen_backup/manifest.py) -- implementá-los seria inventar um contrato novo cross-cutting (gerador + service.py + processoCnj.ts), escopo maior que uma rodada de TDD self-contained, e já teria sido descoberto/sinalizado por duas rodadas anteriores que também investigaram #1610 sem tentar essa parte. Recortar a fatia tribunal<->URL é o mesmo padrão que fechou a metade de política de URL de #1610 em rodadas anteriores (#1622/#1624/#1626): pequeno, testável, e reduz risco real (ameaça 'controle de significado' do issue) sem forçar uma decisão de schema que este tipo de sessão não deveria tomar sozinha."
---

# Decisão: recortar TM-04 para coerência de tribunal, deixando generation id/hash/fingerprint/row-count como follow-up
