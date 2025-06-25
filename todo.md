# TODO - Migração CSV + JSON → DuckDB

## 🎯 Objetivo
Migrar TODOS os dados atualmente dispersos em CSV e JSON para um banco DuckDB unificado, oferecendo consultas SQL avançadas, melhor performance e estrutura consolidada.

## 📋 Tarefas

### Fase 1: Implementação da Classe DuckDB
- [ ] **Criar CausaGanhaDB class**
  - [ ] Schema completo (ratings, partidas, pdf_metadata, decisoes, json_files)
  - [ ] Inicialização automática de tabelas
  - [ ] Context manager para conexões
  - [ ] Métodos CRUD para todas as entidades

- [ ] **Schema de dados unificado**
  - [ ] Tabela `ratings` (TrueSkill μ, σ, total_partidas)
  - [ ] Tabela `partidas` (teams JSON, ratings antes/depois)
  - [ ] Tabela `pdf_metadata` (hash, URLs, Archive.org)
  - [ ] Tabela `decisoes` (JSON completo + metadados)
  - [ ] Tabela `json_files` (rastreamento de arquivos)

- [ ] **Índices e otimização**
  - [ ] Índices por data, processo, hash
  - [ ] Views pré-computadas (ranking, estatísticas)
  - [ ] Campos calculados (conservative_skill)
  - [ ] Foreign keys para integridade

### Fase 2: Scripts de Migração
- [ ] **Migração de CSVs**
  - [ ] `migrate_ratings()` - preservar total_partidas
  - [ ] `migrate_partidas()` - converter formato ELO→TrueSkill
  - [ ] `migrate_pdf_metadata()` - manter status Archive.org
  - [ ] Validação de dados migrados

- [ ] **Migração de JSONs**
  - [ ] `migrate_all_jsons()` - buscar em todos os diretórios
  - [ ] Processar data/, causaganha/data/json/, json_processed/
  - [ ] Extrair decisões para tabela `decisoes`
  - [ ] Rastrear arquivos em `json_files`

- [ ] **Backup e validação**
  - [ ] Backup automático de CSVs/JSONs originais
  - [ ] Validação cruzada de totais
  - [ ] Verificação de integridade
  - [ ] Script de rollback se necessário

### Fase 3: Adaptação do Pipeline
- [ ] **Atualizar pipeline.py**
  - [ ] Substituir lógica CSV por DuckDB
  - [ ] Manter compatibilidade de interface
  - [ ] Transações atômicas para TrueSkill
  - [ ] Rastreamento completo PDF→JSON→Decisão→Partida

- [ ] **Adaptar comandos CLI**
  - [ ] `db stats` - estatísticas gerais
  - [ ] `db ranking` - ranking TrueSkill  
  - [ ] `db query` - consultas SQL diretas
  - [ ] `db backup` - export para CSV

- [ ] **Integração com extractor**
  - [ ] Salvar decisões diretamente no DuckDB
  - [ ] Rastrear JSON files processados
  - [ ] Status de validação por decisão
  - [ ] Link PDF→JSON→Decisões

### Fase 4: Funcionalidades Avançadas
- [ ] **Consultas analíticas**
  - [ ] Evolução temporal de ratings
  - [ ] Estatísticas de performance por advogado
  - [ ] Análise de resultados por tipo de decisão
  - [ ] Métricas de atividade mensal

- [ ] **Processamento JSON**
  - [ ] `process_json_file()` - importar JSON completo
  - [ ] Validação em lote
  - [ ] Status tracking (pending→processing→completed)
  - [ ] Error handling e retry

- [ ] **Views e relatórios**
  - [ ] VIEW ranking_atual (μ, σ, conservative_skill)
  - [ ] VIEW estatisticas_gerais
  - [ ] Ranking por período
  - [ ] Relatórios de atividade

### Fase 5: Performance e Otimização
- [ ] **Otimização de queries**
  - [ ] Benchmark de consultas comuns
  - [ ] Otimizar índices baseado em uso
  - [ ] Views materializadas se necessário
  - [ ] Compressão e vacuum automático

- [ ] **Backup e snapshots**
  - [ ] Snapshots comprimidos para R2
  - [ ] Export incremental
  - [ ] Restore automatizado
  - [ ] Validação de integridade

- [ ] **Monitoramento**
  - [ ] Métricas de performance
  - [ ] Tamanho do banco vs. CSVs/JSONs
  - [ ] Estatísticas de uso
  - [ ] Health checks

### Fase 6: Limpeza e Documentação
- [ ] **Remover código legado**
  - [ ] Código CSV antigo do pipeline
  - [ ] Funções de leitura JSON dispersas
  - [ ] Testes obsoletos
  - [ ] Documentação desatualizada

- [ ] **Documentação nova**
  - [ ] Schema DuckDB completo
  - [ ] Exemplos de consultas SQL
  - [ ] Guia de migração
  - [ ] Troubleshooting

- [ ] **Testes de regressão**
  - [ ] Comparar resultados CSV vs DuckDB
  - [ ] Validar cálculos TrueSkill
  - [ ] Testar backup/restore
  - [ ] Performance benchmarks

## 🔗 Dependências
- DuckDB instalado e funcional
- Dados CSV/JSON atuais preservados
- Pipeline TrueSkill funcionando
- Testes passando

## 📊 Critérios de Sucesso
- [ ] TODOS os dados migrados (CSV + JSON)
- [ ] Pipeline funcional com DuckDB
- [ ] Performance superior a arquivos dispersos
- [ ] Consultas SQL avançadas funcionando
- [ ] Backup/restore validado

## 🚨 Bloqueadores Conhecidos
- Formato JSON inconsistente entre arquivos
- Dados de TrueSkill vs ELO histórico
- Tamanho final do banco DuckDB
- Compatibilidade com R2 snapshots

## 📝 Notas
- DuckDB oferece SQL completo + performance
- JSON nativo simplifica estruturas complexas
- Schema versionado permite evolução
- Banco único facilita backup/deploy
- Consultas ad-hoc para análises avançadas

## 🎯 Resultado Esperado
- Arquivo único `causaganha.duckdb` (~10-50MB)
- Eliminação de 50+ arquivos CSV/JSON dispersos
- Consultas SQL nativas para análises
- Integridade referencial garantida
- Foundation para crescimento futuro