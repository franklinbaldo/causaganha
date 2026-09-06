---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-6x90uc-decision-hardcoded-declared-fields"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
goal_id: "2026-09-06-exciting-mccarthy-6x90uc-goal-schema-drift-detection"
question: "Como determinar, em Python, o conjunto de colunas 'declaradas' por tipo para comparar contra as chaves de frontmatter, dado que knowledge/okf.schema.sql é a fonte de verdade mas scripts/check_agent_run_completeness.py já mantém sua própria cópia da forma de cada tabela em dicts Python (REQUIRED_TEXT_FIELDS_BY_TYPE, REQUIRED_LIST_FIELDS_BY_TYPE, ENUM_FIELDS_BY_TYPE)?"
choice: "Adicionar um dict OPTIONAL_FIELDS_BY_TYPE (goal_id em AgentDecision/AgentEvidence/AgentCheck; evidence_id em AgentCheck) e uma função declared_fields_for_type() que é a união de todos os dicts existentes mais OPTIONAL_FIELDS_BY_TYPE mais {'type'}, em vez de parsear knowledge/okf.schema.sql em runtime com um parser SQL ad-hoc."
rationale: "O próprio módulo já declara, no seu docstring, a estratégia de 're-implementar o contrato em Python, espelhando cada tabela campo por campo' — porque okf-parser não impõe as constraints do .sql. Adicionar um parser de SQL ad-hoc só para extrair nomes de coluna trocaria uma dependência já existente (manter os dicts sincronizados manualmente com o .sql, como REQUIRED_*_BY_TYPE já exige) por uma nova fonte de bugs, para um ganho marginal. Verificado antes de implementar que a união das chaves já declaradas cobre exatamente as colunas de knowledge/okf.schema.sql (incluindo as opcionais goal_id/evidence_id, antes não modeladas em nenhum dict) e que nenhum dos 19 relatórios já existentes usa uma chave fora desse conjunto — logo o reforço não introduz falso positivo."
---

# Decisão: fonte da lista de campos declarados

Espelhar `knowledge/okf.schema.sql` em dicts Python explícitos (consistente com a estratégia já documentada do módulo), em vez de parsear o `.sql` em runtime.
