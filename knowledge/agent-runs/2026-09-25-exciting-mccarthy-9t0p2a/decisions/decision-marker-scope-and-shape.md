---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-9t0p2a-decision-marker-scope-and-shape"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
question: "Onde no schema colocar o marcador de confianca de conteudo (envelope do resultado vs. cada item), e quais tools/campos cobrir nesta rodada?"
choice: "Marcador (tipo_conteudo=Literal['untrusted_legal_text'], default via causaganha_mcp.evidence.UNTRUSTED_LEGAL_TEXT) adicionado ao modelo de cada item (PublicacaoResult, DecisaoResult), nao ao envelope de resultado. Escopo restrito as duas tools que o corpo de #1616 cita explicitamente (publicacoes_buscar, decisoes_buscar); os campos de texto livre de processo_consultar (DocumentoResult.resumo, StjAcordaoResult.tese/ementa) ficam fora desta rodada."
rationale: "O item, nao o envelope, e a unidade que carrega o texto potencialmente adversarial (trecho); colocar o marcador no envelope diluiria o sinal quando um resultado mistura itens com e sem trecho. Colocar no item tambem evitou qualquer mudanca em tests/causaganha_mcp/test_tool_schema.py::_EXPECTED_OUTPUT_FIELDS, que fixa as chaves de nivel superior de cada tool -- um teste de regressao independente que continua protegendo o contrato de topo sem precisar saber sobre o marcador novo. Quanto ao escopo: DocumentoResult/StjAcordaoResult/JurisDecisaoResult em src/causaganha_mcp/tools/processo.py sao gerados por scripts/generate_okf_domain_models.py a partir de TypeContracts em knowledge/ (confirmado comparando os nomes de campo com src/causaganha_mcp/_generated/domain_models.py) -- adicionar um campo la exigiria uma mudanca de TypeContract OKF + regeneracao + migracao dos testes de drift correspondentes (tests/causaganha_mcp/test_okf_domain_models.py, tests/web/test_generate_okf_zod_schemas.py), um escopo maior e com um mecanismo de mudanca diferente (codegen, nao edicao direta de Pydantic) do que cabe com seguranca na mesma rodada junto do resto do trabalho de TDD. Fica registrado como proximo avanco natural."
---

# Decisao: marcador por item, escopo restrito as duas tools citadas por #1616

`tipo_conteudo` foi adicionado a `PublicacaoResult` e `DecisaoResult`
(nao aos envelopes `PublicacoesBuscarResult`/`DecisoesBuscarResult`), com
default `UNTRUSTED_LEGAL_TEXT` centralizado em `causaganha_mcp.evidence`
para as duas tools compartilharem a mesma constante em vez de duplicar a
string literal. Campos de texto livre gerados por codegen OKF em
`processo_consultar` (`resumo`, `tese`, `ementa`) ficam fora desta rodada
-- mudanca de TypeContract, nao apenas de modelo Pydantic; registrado em
`next_move`.
