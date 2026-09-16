---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-zrek2s-decision-follow-scheduled-scaffold-verified-live-state"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
question: "knowledge/agent-runs/index.md e .claude/hourly-loop.md declaram o mecanismo AgentRun legado, e o lote 6 mais recente de #1050 rodou sob Wisk, nao AgentRun -- confirmando que os dois mecanismos agora se alternam na MESMA linhagem de trabalho, nao so em areas distintas do repo. O prompt desta sessao agendada continua instruindo o scaffold legado sem ressalva. Qual mecanismo usar, e como escolher trabalho sem duplicar o que o lote Wisk 6 ja fez?"
choice: "Seguir a instrucao explicita do prompt agendado (criar este AgentRun via .claude/agent-run-scaffold.md, como toda a linhagem desde bueov4/6kxfkh), sem reenviar notificacao proativa sobre a tensao em si. Verificar o estado real do corpus AO VIVO (document_count, tribunal_counts, ids ja usados) via scripts/segmenter_governance_status.py e SegmenterDatasetStore antes de selecionar candidatos do lote 7, em vez de confiar no ultimo numero registrado por uma rodada AgentRun anterior."
rationale: "O precedente de 4 decisoes anteriores (to0ars, bueov4, ez5wkn, 6kxfkh) e consistente e nao foi contradito por nenhum fato novo que aumente a urgencia de uma nova escalada humana -- a tensao ja foi comunicada uma vez com contexto completo (to0ars, 2026-09-14) e o dono ainda nao reconciliou os dois mecanismos, o que e uma decisao dele, nao evidencia de que o schedule foi descontinuado silenciosamente. O fato novo desta rodada (lote 6 rodou sob Wisk, nao AgentRun) e uma clarificacao tecnica sobre COMO os dois mecanismos interagem, nao uma mudanca que demande decisao humana nova: as duas rodadas continuam avancando a mesma issue de forma correta e sem sobreposicao, desde que cada uma parta do estado real do repositorio -- que e, e sempre foi, a fonte de verdade (confirmado ao vivo: document_count=96, nao o 86 que um AgentRun desatualizado sugeriria). Verificar o estado ao vivo antes de escolher candidatos e a mitigacao correta e suficiente para o risco real (duplicar trabalho), sem exigir trocar de mecanismo de relatorio nem pausar a rodada para pedir permissao."
---

# Decisao: manter o scaffold AgentRun, verificar estado ao vivo antes de escolher o lote 7

Mesma decisao de fundo que bueov4/6kxfkh (seguir o prompt agendado
explicito sem reenviar a notificacao ja feita), com um refinamento
concreto motivado pelo achado desta rodada: como o lote 6 mais recente
de #1050 rodou sob Wisk (nao AgentRun), o numero de documentos registrado
pela ultima rodada AgentRun (mg2tp1, lote 4, 86 documentos) esta
desatualizado. Antes de selecionar candidatos para o lote 7, verifiquei
ao vivo via `scripts/segmenter_governance_status.py` e
`SegmenterDatasetStore.list_documents()` que o estado real e
`document_count=96`, 25 tribunais representados (24 alem de TJRO), com
os IDs de documento ja usados extraidos diretamente do `source_uri` de
cada `DocumentRecord` no store -- garantindo que o lote 7 nao repita
nenhum candidato ja ingerido por nenhuma rodada anterior, AgentRun ou
Wisk.
