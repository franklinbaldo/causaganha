---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-230b86-decision-close-1610"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-datajud-merge"
question: "Apos mesclar #1651 (datajud), TM-03/TM-04 ainda tem gap tratavel que justifique manter #1610 aberta, ou o criterio de conclusao da issue esta satisfeito?"
choice: "Fechar #1610 (state_reason=completed), com comentario explicando cada item do criterio de conclusao e citando explicitamente as duas lacunas que ficam de fora por decisao ja registrada (stj sem pipeline de export; hash/row-count completo fora de alcance sem revisao maior de httpfs)."
rationale: "Reli o criterio de conclusao da issue (4 checkboxes) e a matriz completa em docs/SECURITY_THREAT_MODEL.md apos o merge de #1651: validador central de URL feito (TM-03, Python+TS); nenhum read_parquet recebe URL de manifest sem validacao (djen/juris/datajud, incluindo mes_ano do manifesto juris); invariantes de identidade/tribunal/geracao verificados antes da composicao para os tres emissores sob controle deste repo (djen/juris/datajud); regressoes cobertas por teste nos dois runtimes. As duas lacunas restantes (stj, hash completo) sao decisoes ja registradas por rodadas anteriores como fora de alcance, nao pendencias esquecidas -- manter a issue aberta indefinidamente esperando por elas sem nenhum plano de fecha-las divergiria do padrao do proprio SECURITY_THREAT_MODEL.md (secao 4.5: fechamento exige gate executavel, 'salvo quando a linha estiver explicitamente marcada como risco aceito/out of scope')."
---

# Decisão: fechar #1610

O critério de conclusão da issue está satisfeito para tudo que está sob
controle deste repositório. As duas lacunas remanescentes (`stj` sem
pipeline de export próprio; hash/row-count completo, que exigiria baixar
o arquivo inteiro e contradiria o uso de `httpfs`) já eram decisões
registradas por rodadas anteriores, não pendências — manter a issue
aberta por elas indefinidamente não tem um gate executável associado.
