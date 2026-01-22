# Plano de Unificação da Arquitetura CausaGanha

**Objetivo**: Eliminar a separação entre v2/ e legacy (infrastructure/domain/application), criando uma estrutura única e clara que representa a versão atual do sistema.

## 📊 Análise de Dependências (Atual)

### Dependências de v2/ em legacy:
```python
# v2/pipeline/archive.py
from causaganha.infrastructure.clients.archive import ArchiveService, create_archive_service
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.infrastructure.clients.preservation import PreservationService

# v2/pipeline/score.py
from causaganha.domain.scoring.openskill import create_rating, get_openskill_model, rate_teams

# cli.py
from causaganha.infrastructure.clients.archive import create_archive_service
from causaganha.infrastructure.clients.document import DocumentService
```

### Código morto (apenas usado por testes legacy):
- `application/` (16 referências - todas em testes)
- `ml/` (usado apenas internamente e por testes)
- `schemas/` (usado apenas internamente e por testes)
- `validation/` (usado apenas por testes)

### Duplicações identificadas:
- `infrastructure/ai/` ≈ `v2/analysis/` (vector_store, analyzer, embeddings)
- `infrastructure/storage/` ≈ `v2/storage/` (connection, queries, repositories)
- `infrastructure/integrations/pje/` ≈ `v2/api/` (PJe client)

---

## 🎯 Estrutura Unificada (Alvo)

```
src/causaganha/
├── cli/                           # CLI modularizado (898 linhas → ~100-150/arquivo)
│   ├── __init__.py                # App Typer principal
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── collect.py             # causaganha collect
│   │   ├── analyze.py             # causaganha analyze
│   │   ├── score.py               # causaganha score
│   │   ├── archive.py             # causaganha archive
│   │   ├── pipeline.py            # causaganha pipeline
│   │   ├── db.py                  # causaganha db
│   │   ├── export.py              # causaganha export-parquet, export-status
│   │   ├── parquet.py             # causaganha parquet (subcomandos)
│   │   └── groundtruth.py         # causaganha groundtruth (subcomandos)
│   └── utils.py                   # Error handling, formatação
│
├── api/                           # PJe API client
│   ├── __init__.py
│   └── client.py                  # De v2/api/client.py
│
├── analysis/                      # Decision analysis & ML
│   ├── __init__.py
│   ├── analyzer.py                # LLM analyzer (Pydantic AI)
│   ├── rag_analyzer.py            # RAG-only analyzer
│   ├── hybrid_analyzer.py         # Hybrid strategy
│   ├── embedding_service.py       # ← RENOMEAR de embedding_service_v2.py
│   ├── embedding_models.py        # Model configs (Jina, Google)
│   ├── providers.py               # Provider implementations
│   ├── vector_store.py            # Vector store (única implementação)
│   ├── models.py                  # DecisionAnalysis Pydantic models
│   ├── strategy.py                # Analysis strategy enum
│   └── text_chunker.py            # Text chunking
│
├── pipeline/                      # Orchestration workflows
│   ├── __init__.py
│   ├── collect.py                 # Intimation collection
│   ├── analyze.py                 # Decision analysis
│   ├── score.py                   # Rating calculation
│   ├── archive.py                 # Document archiving
│   ├── analyze_parquet.py         # Parquet analysis
│   ├── parquet_export.py          # Parquet export
│   ├── ia_download.py             # Internet Archive download
│   ├── ia_upload.py               # Internet Archive upload
│   ├── embedding_pipeline.py      # Embedding generation
│   └── export_orchestrator.py     # Export coordination
│
├── storage/                       # DuckDB data layer
│   ├── __init__.py
│   ├── connection.py              # Ibis-DuckDB connection
│   ├── queries.py                 # CRUD operations
│   ├── migrations.py              # Migration tracker
│   ├── schema.sql                 # DuckDB schema DDL
│   ├── embedding_storage.py       # Embedding storage
│   └── migrations/
│       ├── 001_add_rag_support.sql
│       └── 002_add_parquet_exports.sql
│
├── clients/                       # External service clients
│   ├── __init__.py
│   ├── archive.py                 # ← De infrastructure/clients/
│   ├── document.py                # ← De infrastructure/clients/
│   ├── preservation.py            # ← De infrastructure/clients/
│   └── constants.py               # ← De infrastructure/clients/
│
├── scoring/                       # Rating system
│   ├── __init__.py
│   └── openskill.py               # ← De domain/scoring/
│
├── models/                        # Domain models
│   ├── __init__.py
│   ├── intimation.py              # ← Extrair de domain/models.py
│   ├── party.py                   # ← Extrair de domain/models.py
│   ├── lawyer.py                  # ← Extrair de domain/models.py
│   └── analysis.py                # ← De domain/models_analysis.py
│
├── utils/
│   └── __init__.py
│
├── config.py                      # Settings (já existe)
└── __init__.py

legacy_archive/                    # Código legado (não usado pela versão atual)
├── v1/                            # V1 original (já arquivado)
├── application/                   # ← Mover de src/causaganha/application/
├── infrastructure/                # ← Mover de src/causaganha/infrastructure/
│   ├── ai/                        # (duplicado com analysis/)
│   ├── storage/                   # (duplicado com storage/)
│   ├── integrations/              # (duplicado com api/)
│   └── cloud/                     # Cloud functions (manter separado? verificar uso)
├── domain/                        # ← Mover de src/causaganha/domain/
│   ├── interfaces.py
│   ├── factories.py
│   └── services/
├── ml/                            # ← Mover de src/causaganha/ml/
├── schemas/                       # ← Mover de src/causaganha/schemas/
└── validation/                    # ← Mover de src/causaganha/validation/
```

---

## 🔄 Plano de Migração (7 Fases)

### **FASE 1: Remover Duplicações de Embeddings** ⚡ (1 dia)

**Objetivo**: Eliminar redirects desnecessários.

**Passos**:
```bash
# 1. Deletar redirects
rm src/causaganha/v2/analysis/embedding_service.py
rm src/causaganha/v2/analysis/embedding_providers.py

# 2. Renomear v2 → principal
mv src/causaganha/v2/analysis/embedding_service_v2.py \
   src/causaganha/v2/analysis/embedding_service.py

# 3. Atualizar imports em v2/
find src/causaganha/v2 -name "*.py" -exec sed -i \
  's/from causaganha.v2.analysis.embedding_service_v2/from causaganha.v2.analysis.embedding_service/g' {} +
```

**Validação**:
```bash
pytest tests/v2/analysis/test_embedding_providers.py -v
```

---

### **FASE 2: Criar Estrutura Unificada** 📁 (1 dia)

**Objetivo**: Criar diretórios da nova estrutura.

**Passos**:
```bash
# Criar diretórios principais
mkdir -p src/causaganha/cli/commands
mkdir -p src/causaganha/clients
mkdir -p src/causaganha/scoring
mkdir -p src/causaganha/models

# Criar __init__.py
touch src/causaganha/cli/__init__.py
touch src/causaganha/cli/commands/__init__.py
touch src/causaganha/clients/__init__.py
touch src/causaganha/scoring/__init__.py
touch src/causaganha/models/__init__.py
```

---

### **FASE 3: Migrar v2/ para Raiz** 🚀 (2 dias)

**Objetivo**: Mover módulos de v2/ para a raiz de causaganha/.

**Passos**:
```bash
# Mover módulos (usando git mv para preservar histórico)
git mv src/causaganha/v2/api src/causaganha/api
git mv src/causaganha/v2/analysis src/causaganha/analysis
git mv src/causaganha/v2/pipeline src/causaganha/pipeline
git mv src/causaganha/v2/storage src/causaganha/storage
git mv src/causaganha/v2/utils src/causaganha/utils

# Deletar v2/ (agora vazio)
rmdir src/causaganha/v2
```

**Atualizar imports**:
```bash
# Atualizar imports de v2.* → causaganha.*
find src/causaganha tests -name "*.py" -type f -exec sed -i \
  's/from causaganha.v2./from causaganha./g' {} +

find src/causaganha tests -name "*.py" -type f -exec sed -i \
  's/import causaganha.v2./import causaganha./g' {} +
```

**Validação**:
```bash
# Verificar que não há mais imports de v2
grep -r "from causaganha.v2" src/ tests/ && echo "ERRO: Ainda há imports de v2!" || echo "OK"

# Rodar testes V2
pytest tests/v2/ -v
```

---

### **FASE 4: Migrar infrastructure/clients e domain/scoring** 🔧 (2 dias)

**Objetivo**: Mover código legacy usado por v2.

**4.1. Migrar infrastructure/clients/ → clients/**
```bash
# Mover arquivos
git mv src/causaganha/infrastructure/clients/archive.py src/causaganha/clients/
git mv src/causaganha/infrastructure/clients/document.py src/causaganha/clients/
git mv src/causaganha/infrastructure/clients/preservation.py src/causaganha/clients/
git mv src/causaganha/infrastructure/clients/constants.py src/causaganha/clients/

# Atualizar imports
find src/causaganha tests -name "*.py" -type f -exec sed -i \
  's/from causaganha.infrastructure.clients/from causaganha.clients/g' {} +
```

**4.2. Migrar domain/scoring/ → scoring/**
```bash
git mv src/causaganha/domain/scoring/openskill.py src/causaganha/scoring/

# Atualizar imports
find src/causaganha tests -name "*.py" -type f -exec sed -i \
  's/from causaganha.domain.scoring/from causaganha.scoring/g' {} +
```

**4.3. Extrair models de domain/**
```bash
# Criar models/intimation.py (extrair de domain/models.py)
# Criar models/party.py
# Criar models/lawyer.py
# Criar models/analysis.py (de domain/models_analysis.py)

# (Fazer manualmente ou com script Python)
```

**Validação**:
```bash
# Verificar imports
grep -r "from causaganha.infrastructure.clients" src/ tests/ && echo "ERRO" || echo "OK"
grep -r "from causaganha.domain.scoring" src/ tests/ && echo "ERRO" || echo "OK"

# Rodar testes
pytest tests/v2/ -v
pytest tests/unit/test_archive_pipeline.py -v
pytest tests/unit/test_score_pipeline.py -v
```

---

### **FASE 5: Quebrar CLI em Módulos** ✂️ (2 dias)

**Objetivo**: Refatorar cli.py (898 linhas) em módulos menores.

**Estrutura**:
```
src/causaganha/cli/
├── __init__.py              # App Typer + imports de comandos
├── commands/
│   ├── collect.py           # collect()
│   ├── analyze.py           # analyze()
│   ├── score.py             # score()
│   ├── archive.py           # archive()
│   ├── pipeline.py          # pipeline()
│   ├── db.py                # db()
│   ├── export.py            # export_parquet(), export_status()
│   ├── parquet.py           # parquet subcommands
│   └── groundtruth.py       # groundtruth subcommands
└── utils.py                 # _handle_error(), formatação
```

**Passos**:
```bash
# 1. Criar cli/commands/ e extrair comandos
# 2. Atualizar cli/__init__.py para importar comandos
# 3. Deletar cli.py original
# 4. Criar symlink se necessário para compatibilidade
```

**Validação**:
```bash
# Testar comandos CLI
uv run causaganha --help
uv run causaganha collect --help
uv run causaganha analyze --help
uv run causaganha parquet --help
```

---

### **FASE 6: Arquivar Legacy** 📦 (1 dia)

**Objetivo**: Mover código não usado para legacy_archive/.

**Passos**:
```bash
# Criar legacy_archive/
mkdir -p legacy_archive

# Mover código legacy
git mv src/causaganha/application legacy_archive/
git mv src/causaganha/infrastructure legacy_archive/
git mv src/causaganha/domain legacy_archive/
git mv src/causaganha/ml legacy_archive/
git mv src/causaganha/schemas legacy_archive/
git mv src/causaganha/validation legacy_archive/

# Atualizar .gitignore se necessário
echo "legacy_archive/" >> .gitignore  # Opcional
```

**Validação**:
```bash
# Verificar que src/causaganha/ está limpo
ls -la src/causaganha/

# Deve mostrar apenas:
# api/, analysis/, cli/, clients/, models/, pipeline/, scoring/, storage/, utils/, config.py
```

---

### **FASE 7: Atualizar Testes Legacy** 🧪 (2 dias)

**Objetivo**: Atualizar testes que importam de legacy ou marcar como deprecated.

**Opções**:
1. **Atualizar imports** para nova estrutura
2. **Marcar testes como @pytest.mark.skip** (legacy)
3. **Deletar testes** que testam código arquivado

**Recomendação**: Marcar como skip e criar issue para refatorar depois.

```python
# tests/integration/test_pipeline_collect.py
@pytest.mark.skip(reason="Legacy test - uses archived application layer")
def test_run_collection():
    from causaganha.application.pipeline.collect import run_collection
    ...
```

---

## 📋 Checklist de Validação Pós-Migração

### Estrutura:
- [ ] `src/causaganha/v2/` não existe mais
- [ ] `src/causaganha/infrastructure/` movido para `legacy_archive/`
- [ ] `src/causaganha/domain/` movido para `legacy_archive/`
- [ ] `src/causaganha/application/` movido para `legacy_archive/`
- [ ] Estrutura unificada criada (api/, analysis/, cli/, clients/, models/, pipeline/, scoring/, storage/)

### Imports:
- [ ] Nenhum import de `causaganha.v2.*` em src/ ou tests/
- [ ] Nenhum import de `causaganha.infrastructure.clients` em src/ ou tests/
- [ ] Nenhum import de `causaganha.domain.scoring` em src/ ou tests/
- [ ] CLI funciona com nova estrutura

### Testes:
- [ ] `pytest tests/v2/ -v` passa (ou testes movidos para tests/)
- [ ] `pytest tests/unit/ -k "not legacy"` passa
- [ ] `pytest tests/integration/ -k "not legacy"` passa
- [ ] Testes BDD funcionam: `pytest tests/features/ -v`

### CLI:
- [ ] `uv run causaganha --help` funciona
- [ ] `uv run causaganha collect --help` funciona
- [ ] `uv run causaganha analyze --help` funciona
- [ ] `uv run causaganha parquet --help` funciona
- [ ] Todos os comandos executam sem import errors

### Documentação:
- [ ] Atualizar CLAUDE.md com nova estrutura
- [ ] Atualizar README.md (se existir)
- [ ] Criar MIGRATION.md explicando mudanças

---

## 🎯 Métricas de Sucesso

**Antes**:
- 87 arquivos Python
- 3 camadas arquiteturais (v2/, infrastructure/, domain/)
- CLI: 1 arquivo de 898 linhas
- 4 arquivos de embeddings (duplicação)
- 2 implementações de VectorStore

**Depois**:
- ~70-75 arquivos Python (consolidação)
- 1 camada arquitetural única
- CLI: ~10 arquivos de 100-150 linhas cada
- 2 arquivos de embeddings (service + providers)
- 1 implementação de VectorStore

**Ganhos**:
- ✅ -15% arquivos (consolidação)
- ✅ -90% linhas por arquivo CLI (modularização)
- ✅ -50% duplicação (embeddings, vector store)
- ✅ 100% clareza arquitetural (uma única estrutura)
- ✅ 0 dependências de v2/ em legacy

---

## ⏱️ Timeline Estimado

| Fase | Descrição | Duração | Risco |
|------|-----------|---------|-------|
| 1 | Remover duplicações embeddings | 1 dia | Baixo |
| 2 | Criar estrutura unificada | 1 dia | Baixo |
| 3 | Migrar v2/ para raiz | 2 dias | Médio |
| 4 | Migrar infrastructure/domain | 2 dias | Médio |
| 5 | Quebrar CLI em módulos | 2 dias | Baixo |
| 6 | Arquivar legacy | 1 dia | Baixo |
| 7 | Atualizar testes | 2 dias | Médio |
| **TOTAL** | | **11 dias** | |

**Recomendação**: Fazer em 2 sprints (1 semana cada), com validação contínua de testes.

---

## 🚨 Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar imports em testes | Alta | Médio | Rodar pytest após cada fase |
| Perder histórico git | Baixa | Alto | Usar `git mv` ao invés de `mv` |
| CLI parar de funcionar | Média | Alto | Testar comandos após cada mudança |
| Código legado ainda usado | Baixa | Alto | Fazer análise de dependências primeiro (FASE 1) |

---

## 📝 Notas

- Usar `git mv` para preservar histórico do Git
- Rodar testes após CADA fase
- Commitar cada fase separadamente para facilitar rollback
- Criar branch `refactor/unify-architecture` para todo o trabalho
- Fazer code review antes de mergear em main
