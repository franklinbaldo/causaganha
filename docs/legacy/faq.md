# FAQ e Limitações

**Como configurar as chaves de API necessárias?**

### Google Gemini (obrigatório para extração)

- **Para execução via GitHub Actions:** Defina o segredo `GEMINI_API_KEY` nas configurações do repositório GitHub.
- **Para execução local:** Exporte a variável de ambiente:
  ```bash
  export GEMINI_API_KEY="SUA_CHAVE_API_AQUI"
  ```

### Internet Archive (opcional, para upload e sync)

- **GitHub Actions:** Defina os segredos `IA_ACCESS_KEY` e `IA_SECRET_KEY`
- **Local:** Exporte as variáveis:
  ```bash
  export IA_ACCESS_KEY="SUA_CHAVE_IA"
  export IA_SECRET_KEY="SUA_CHAVE_SECRETA_IA"
  ```

### Arquivo .env (recomendado para desenvolvimento local)

Crie um arquivo `.env` na raiz do projeto:

```bash
GEMINI_API_KEY=sua_chave_gemini
IA_ACCESS_KEY=sua_chave_ia
IA_SECRET_KEY=sua_chave_secreta_ia
MAX_CONCURRENT_DOWNLOADS=3
MAX_CONCURRENT_IA_UPLOADS=2
```

**Quais são as principais limitações atuais?**

### Limitações Técnicas

- **Cotas da API Gemini:** O sistema inclui rate limiting automático, mas exceder as cotas gratuitas (15 RPM, 500 requests/dia) pode interromper a extração.
- **Dependência do Internet Archive:** O sistema distribuído depende da disponibilidade do IA para sincronização. Falhas no IA podem afetar a colaboração entre ambientes.
- **Concorrência limitada:** Para respeitar os servidores TJRO, downloads são limitados a 3 simultâneos por padrão.

### Limitações de Dados

- **Fonte de Dados Única:** Atualmente configurado apenas para TJRO, mas arquitetura suporta expansão.
- **Identificação de Advogados:** Baseada em normalização de nomes. Colisões possíveis sem números OAB claros.
- **Interpretação LLM:** Dependência da qualidade do Gemini para parsing de PDFs complexos.

### Melhorias Recentes

- **Sistema de locks:** Previne corrupção por acessos concorrentes
- **Rate limiting inteligente:** Backoff exponencial automático
- **Resumo de progresso:** Funcionalidade `--stats-only` para monitoramento
- **Chunk processing:** PDFs grandes processados em segmentos com overlap

**Como baixar manualmente o Diário ou resolver problemas de download?**

### Download Manual

1. **Último diário:** https://www.tjro.jus.br/diario_oficial/ultimo-diario.php
2. **Por data:** Navegue no site TJRO ou use nosso pipeline
3. **Do Internet Archive:** Use `uv run python src/ia_discovery.py --year 2025` para encontrar URLs diretas

### Troubleshooting de Downloads

```bash
# Verificar status dos downloads recentes
uv run python src/async_diario_pipeline.py --stats-only

# Forçar reprocessamento de item falhado
uv run python src/async_diario_pipeline.py --force-reprocess --max-items 1

# Reduzir concorrência se houver timeouts
uv run python src/async_diario_pipeline.py --concurrent-downloads 1
```

### Problemas de "Página Bloqueada"

- O pipeline inclui headers apropriados e delays entre requests
- Se persistir, use `--concurrent-downloads 1` para reduzir carga no servidor TJRO

**Como funciona o sistema distribuído de banco de dados?**

O CausaGanha usa um banco DuckDB compartilhado via Internet Archive:

### Arquitetura

1. **Banco local:** `data/causaganha.duckdb` para operações rápidas
2. **Banco no IA:** `causaganha-database-live` para compartilhamento
3. **Sistema de locks:** Previne conflitos entre PC e GitHub Actions

### Comandos de Sincronização

```bash
# Verificar status
uv run python src/ia_database_sync.py status

# Sincronizar (baixar do IA se necessário)
uv run python src/ia_database_sync.py sync

# Upload manual
uv run python src/ia_database_sync.py upload

# Forçar download (sobrescrever local)
uv run python src/ia_database_sync.py download --force
```

### Resolução de Conflitos

- **Lock ativo:** Sistema aguarda automaticamente ou use `--force`
- **Hash mismatch:** O sync inteligente resolve automaticamente
- **Arquivo corrompido:** Use `download --force` para restaurar

**Como monitorar progresso do processamento massivo?**

### Comandos de Monitoramento

```bash
# Estatísticas do pipeline assíncrono
uv run python src/async_diario_pipeline.py --stats-only

# Cobertura no Internet Archive
uv run python src/ia_discovery.py --coverage-report --year 2025

# Status do banco distribuído
uv run python src/ia_database_sync.py status

# Progresso detalhado (durante execução)
uv run python src/async_diario_pipeline.py --verbose --max-items 10
```

### Arquivos de Progresso

- `data/diario_pipeline_progress.json`: Progresso detalhado por item
- `data/causaganha.duckdb`: Banco com todos os dados processados
- Logs detalhados durante execução com `--verbose`

**Como processar apenas diários de um período específico?**

```bash
# Por ano (arquivo predefinido)
uv run python src/async_diario_pipeline.py --input data/diarios_2025_only.json

# Por intervalo de datas
uv run python src/async_diario_pipeline.py --start-date 2025-01-01 --end-date 2025-06-26

# Limitar quantidade para testes
uv run python src/async_diario_pipeline.py --max-items 10

# Combinar filtros
uv run python src/async_diario_pipeline.py --input data/diarios_2025_only.json --max-items 50
```

### Troubleshooting Geral

Se encontrar erros de rede ou limites de API durante o processamento:

```bash
# Repetir a operação com verbosidade para identificar o problema
uv run python src/async_diario_pipeline.py --verbose --max-items 1

# Caso atinja o limite da API Gemini, aguarde alguns minutos e tente novamente
uv run python src/async_diario_pipeline.py --resume
```

Para falhas persistentes, verifique se há conexão estável e consulte os logs em `logs/` para detalhes adicionais.

## Troubleshooting de Analytics

Se os comandos de analytics não exibirem resultados ou apresentarem erros:

```bash
# Verificar se o banco distribuído está sincronizado
uv run python src/ia_database_sync.py status

# Executar um resumo de tendências de decisões (exemplo)
causaganha analytics outcome-trend --limit 50
```

- Certifique-se de que `data/causaganha.duckdb` está atualizado e acessível
- Utilize a opção `--refresh` para forçar nova coleta de dados quando necessário
- Consulte `logs/analytics.log` para mensagens detalhadas de erro

## Multi-tribunal

O pipeline suporta adaptadores para diferentes tribunais. Utilize a opção
`--tribunal` para especificar qual diário processar.
Consulte `docs/examples/diario_processing_example.py` para um script completo que
mostra essa funcionalidade.

```bash
# Processar diário do TJSP
causaganha pipeline run --tribunal TJSP --date 2025-06-24

# Processar diário do TJMG
causaganha pipeline run --tribunal TJMG --date 2025-06-24
```

## Diario Dataclass

**O que é a `Diario` Dataclass?**

A `Diario` dataclass (`src/models/diario.py`) é uma representação unificada de um diário judicial dentro do sistema CausaGanha. Ela foi introduzida para padronizar a forma como os dados dos diários são manipulados, independentemente do tribunal de origem.

**Quais são os principais campos da `Diario` Dataclass?**

- `tribunal`: Identificador do tribunal (ex: 'tjro').
- `data`: Data de publicação do diário.
- `url`: URL do diário.
- `filename`: Nome do arquivo PDF (opcional).
- `status`: Status do processamento (ex: 'pending', 'downloaded').
- Outros campos opcionais como `hash`, `pdf_path`, `ia_identifier`, `metadata`.

**Como a `Diario` Dataclass é utilizada?**

Ela é usada em conjunto com interfaces como `DiarioDiscovery`, `DiarioDownloader`, e `DiarioAnalyzer` para criar um fluxo de processamento de diários mais modular e extensível. A CLI também está sendo adaptada para usar esta dataclass, por exemplo, com o flag `--as-diario`. Consulte o tutorial em `docs/tutorials/diario_dataclass_tutorial.ipynb` para mais detalhes.

## Migração do Banco de Dados para dbt-duckdb (DTB)

**Por que estamos migrando para `dbt-duckdb`?**

A migração para `dbt-duckdb` visa simplificar o gerenciamento do esquema do banco de dados, transformações de dados, testes e documentação, utilizando `dbt` como ferramenta principal. Isso melhora a reprodutibilidade, a qualidade dos dados e facilita a manutenção.

**Como essa migração afeta o desenvolvimento?**

- **Definição de Esquema**: O esquema do banco de dados será definido por modelos SQL no diretório `dbt/models/` em vez de migrações tradicionais (como Alembic).
- **Workflow Local**: Os desenvolvedores usarão comandos `dbt` (ex: `dbt build`, `dbt run`, `dbt test`) para construir e testar o banco de dados localmente.
- **CLI**: O comando `causaganha db migrate` será atualizado para executar `dbt build`.
- **Estrutura de Dados**: Espera-se uma organização em camadas `staging` (dados brutos) e `marts` (dados analíticos).

**Onde encontro mais informações sobre a migração para dbt e o novo esquema?**

Consulte o guia do desenvolvedor em `docs/developer/database_migration_dbt.md`. Ele detalha o processo de setup, conceitos chave do dbt, workflow de desenvolvimento e a abordagem para o novo esquema.
