---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-5ov0kv-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-6kxfkh/run.md (ultima rodada mesclada antes desta), PR #1527 (bc9ae6, mesclada nesta rodada)"
finding: "Tensao AgentRun-vs-Wisk confirmada, inalterada desde a ultima avaliacao (6kxfkh, mesma tarde de hoje): knowledge/agent-runs/index.md e .claude/hourly-loop.md instruem usar exclusivamente o runtime Wisk e proibem novos AgentRuns; o prompt desta sessao agendada continua, sem ressalva, instruindo o scaffold legado. Escalado uma vez por to0ars (14/09) via notificacao proativa; nenhum fato novo desde a ultima reconfirmacao justifica reenviar. Decisao desta rodada: seguir o prompt agendado (mesmo padrao de toda a linhagem desde bueov4), documentado em decision-follow-scheduled-scaffold-again. Achado operacional novo desta rodada, distinto de tudo que rodadas anteriores viram: ha AGORA duas ou mais sessoes desta mesma linhagem rodando concorrentemente sobre o mesmo repositorio no mesmo minuto (esta rodada e bc9ae6, cujo PR #1527 foi descoberto ja aberto e com CI verde ao consultar PRs abertas) -- nao apenas rodadas sequenciais uma apos a outra. Isso nao muda a decisao AgentRun-vs-Wisk, mas e um fato operacional relevante para uma rodada futura avaliar (risco de trabalho duplicado/colisao em data/segmenter/reviews/ se duas sessoes escolherem os mesmos documentos-alvo ao mesmo tempo; mitigado nesta rodada apenas porque a outra sessao chegou primeiro e pode ser mesclada e re-sincronizada antes de escolher novo trabalho, nao por nenhum lock real)."
---

# Leitura: conhecimento OKF relevante

Lido `knowledge/agent-runs/index.md` e `.claude/hourly-loop.md` na integra:
confirmam a mesma tensao (mecanismo `AgentRun` e legado, loop horario
migrado para Wisk, prompt agendado desta sessao ainda instrui o scaffold
legado sem ressalva) ja identificada e escalada por rodadas anteriores
(njkncp, vd5dfq em 11/09; bueov4, to0ars em 14/09). Reconfirmado ao vivo:
nada mudou desde a ultima reconfirmacao (6kxfkh, ~18:53 de hoje) -- decisao
desta rodada e continuar seguindo o prompt agendado, sem reenviar a mesma
notificacao sem fato novo.

Achado operacional novo: ao consultar PRs abertas para esta rodada
(reading-prs), encontrei a PR #1527 ja aberta, com CI verde, produzida por
uma sessao concorrente (branch bc9ae6) resolvendo exatamente os dois
documentos que esta rodada tinha acabado de escolher como proximo
incremento. Isso indica que multiplas instancias desta rotina agendada
estao rodando em paralelo sobre o mesmo repositorio, nao apenas em
sequencia -- um padrao que nenhuma rodada anterior lida registrou
explicitamente (todas descreviam "a ultima rodada" como ja mesclada antes
do inicio da atual). Tratado nesta rodada como continuidade (mesclar o
trabalho pronto, ressincronizar, seguir para o proximo incremento) em vez
de descarte ou duplicacao -- ver decision-merge-in-flight-pr. O front de
dominio real segue #1051: review_count/evaluation_eligible_count 23 -> 25
apos o merge desta rodada de #1527; pool de candidatos com exatamente uma
anotacao unseeded cai de 21 para 19.
