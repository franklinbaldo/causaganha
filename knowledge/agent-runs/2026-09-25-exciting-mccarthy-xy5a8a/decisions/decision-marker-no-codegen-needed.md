---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-xy5a8a-decision-marker-no-codegen-needed"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
goal_id: "2026-09-25-exciting-mccarthy-xy5a8a-goal-processo-consultar-evidence-marker"
question: "O follow-up de #1616 para processo_consultar exige mudar o TypeContract OKF e regenerar src/causaganha_mcp/_generated/domain_models.py, como registrado pela rodada anterior (9t0p2a), ou o marcador pode ser adicionado diretamente ao schema Pydantic ja escrito a mao da tool?"
choice: "Adicionar tipo_conteudo diretamente as classes Pydantic escritas a mao DocumentoResult e StjAcordaoResult em src/causaganha_mcp/tools/processo.py -- o mesmo padrao Literal['untrusted_legal_text'] + Field(default=UNTRUSTED_LEGAL_TEXT) ja usado em publicacoes.py/decisoes.py -- sem alterar o bundle OKF (knowledge/contracts/) nem regenerar _generated/domain_models.py."
rationale: "A PR #1627 registrou o follow-up de processo_consultar como dependente de 'TypeContract change plus regenerating the drift-checked generated files'. Leitura direta do codigo mostrou que essa premissa nao se aplica: DocumentoResult/StjAcordaoResult (definidas em tools/processo.py) sao o schema publico real da tool MCP -- o que test_tool_output_schema_declares_the_content_trust_marker inspeciona via tool.output_schema['$defs']. O gerador scripts/generate_okf_domain_models.py produz apenas _generated/domain_models.py, usado internamente por processo_contract.serialize_shared_core() para validar a composicao do dossie e devolver um dict simples -- esse dict e passado como **kwargs para ProcessoConsultarResult(...), entao o valor default do campo Pydantic hand-written e suficiente sem qualquer mudanca no gerador. Tratar o marcador como parte do contrato OKF do dominio (Processo/DocumentoProcesso/StjAcordao) misturaria uma preocupacao de seguranca da camada de apresentacao MCP com o modelo de dominio interno, que tambem alimenta o dashboard web sem esse conceito de 'instrucao vs evidencia' (esse e um problema de agente, nao do dado em si) -- manter o marcador na camada de tools, como ja feito para as outras duas tools, e mais simples e mais coerente com o estado atual do produto."
---

# Decisão: marcador fica na camada de tools MCP, não no contrato OKF de domínio

Confirma e corrige a suposição registrada pela rodada anterior (`9t0p2a`)
de que estender o marcador a `processo_consultar` exigiria uma mudança de
`TypeContract` e regeneração de código. O schema publicado pela tool é
definido à mão em `tools/processo.py`, igual às outras duas tools —
adicionar o campo lá é suficiente e mantém o padrão já estabelecido.
