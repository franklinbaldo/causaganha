---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-xy5a8a-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-25-exciting-mccarthy-9t0p2a/run.md e knowledge/agent-runs/2026-09-25-exciting-mccarthy-r2xele/run.md (relatorios mais recentes na mesma janela de seguranca)"
finding: "9t0p2a (rodada que abriu e mesclou a PR #1627) fechou o nucleo de #1616 para publicacoes_buscar/decisoes_buscar e registrou explicitamente, no proprio corpo da PR e no result_summary do run.md, que os campos de texto de processo_consultar (DocumentoResult.resumo, StjAcordaoResult.tese/ementa) ficaram fora de escopo -- descritos ali como dependentes de 'TypeContract change plus regenerating the drift-checked generated files'. Investigacao desta rodada (leitura direta de src/causaganha_mcp/tools/processo.py e processo_contract.py) mostrou que essa premissa estava incorreta: DocumentoResult/StjAcordaoResult sao classes Pydantic escritas a mao no proprio tools/processo.py (o schema publico real da tool), nao emitidas por scripts/generate_okf_domain_models.py -- esse gerador so produz src/causaganha_mcp/_generated/domain_models.py, consumido internamente por processo_contract.serialize_shared_core() para validar a composicao do dossie antes de devolver um dict simples que popula ProcessoConsultarResult(**shared). O marcador podia, portanto, ser adicionado exatamente como em publicacoes.py/decisoes.py, sem tocar o bundle OKF nem regenerar nada -- decisao registrada em decision-marker-no-codegen-needed. r2xele (rodada seguinte, TDD em TypeScript sobre #1610) nao tocou #1616; confirma que nenhuma rodada entre 9t0p2a e esta reabriu o follow-up de processo_consultar."
---

# Leitura: conhecimento OKF relevante

Revisado o relatorio que fechou o nucleo de `#1616` (`9t0p2a`) e o
relatorio mais recente da mesma janela (`r2xele`). O primeiro registrou
como follow-up a extensao do marcador para `processo_consultar`, supondo
que exigiria mudanca de TypeContract e regeneracao de codigo. A leitura
direta do codigo nesta rodada mostrou que essa suposicao nao se sustenta
para o schema publico da tool (`tools/processo.py` e escrito a mao) --
decisao registrada explicitamente para nao repetir esse desvio de escopo
em rodadas futuras.
