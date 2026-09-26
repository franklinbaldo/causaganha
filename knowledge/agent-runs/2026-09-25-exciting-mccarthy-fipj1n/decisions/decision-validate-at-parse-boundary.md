---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-fipj1n-decision-validate-at-parse-boundary"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
question: "Onde validar mes_ano: em ManifestJuris.load_text (o parser do CSV do manifesto), em _juris_url (o ponto que constrói a URL), ou reaproveitando/estendendo _validate_artifact_url de causaganha.processos.service (o validador central já usado para arquivo_ia_url)?"
choice: "Validar em ManifestJuris.load_text, no mesmo loop de linha que já rejeita coluna ausente/n_docs não numérico com ManifestFormatError — não em _juris_url nem reaproveitando _validate_artifact_url."
rationale: "_validate_artifact_url em processos/service.py valida uma URL já completamente formada (host/scheme/path/query) — mes_ano é um campo estrutural de uma linha de manifesto, não uma URL, então reaproveitar aquele validador exigiria primeiro montar a URL para só então rejeitá-la, adiando a falha para o pior lugar possível (depois que a string perigosa já existe). Validar em _juris_url é tecnicamente correto mas exigiria checagem redundante toda vez que a função roda, e um manifesto malformado só é descoberto no meio da conversão para datasets em vez de no parse. Validar em load_text é o padrão já estabelecido na própria função (n_docs não numérico já levanta ManifestFormatError ali) e falha o mais cedo possível, antes que a entrada entre em qualquer estrutura de dados do domínio — e como load_text já é chamada por discover_published_juris_datasets antes de _juris_url, a proteção é automática lá também. O ManifestFormatError propagado já é capturado por causaganha_mcp/tools/decisoes.py junto com httpx.HTTPError, degradando para uma 'limitação' registrada em vez de crashar decisoes_buscar — infraestrutura de degradação graciosa já existente, zero plumbing adicional necessário."
---

# Decisão: validar `mes_ano` no parser do manifesto, não na URL

`ManifestJuris.load_text` já é o único ponto de entrada de dados não
confiáveis nesta cadeia (o manifesto é buscado ao vivo de `archive.org`)
e já tem o padrão estabelecido de levantar `ManifestFormatError` em linha
malformada. Validar ali, e não em `_juris_url` ou via
`_validate_artifact_url`, falha o mais cedo possível e reaproveita a
infraestrutura de degradação graciosa que `causaganha_mcp/tools/decisoes.py`
já tem para `ManifestFormatError`.
