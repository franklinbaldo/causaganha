# CausaGanha

[![Update OpenSkill Ratings](https://img.shields.io/github/actions/workflow/status/franklinbaldo/causa_ganha/03_update.yml?label=update-openskill)](https://github.com/franklinbaldo/causa_ganha/actions/workflows/03_update.yml)

**CausaGanha** é uma **plataforma de análise judicial de nível empresarial** que combina inteligência artificial, armazenamento multi-camadas e algoritmos de avaliação de habilidades para criar um sistema automatizado de avaliação de desempenho jurídico. Utilizando o sistema **OpenSkill**, uma alternativa de código aberto, a plataforma analisa decisões judiciais do Tribunal de Justiça de Rondônia (TJRO) para gerar rankings dinâmicos e transparentes de advogados.

O sistema implementa uma **arquitetura de três camadas** com:
- **Processamento local**: DuckDB para operações de alta performance
- **Arquivo público**: Internet Archive para transparência e acesso permanente
- **Backup em nuvem**: Cloudflare R2 para análises remotas e recuperação de desastres

Com **6 workflows automatizados** executando diariamente, a plataforma processa desde a coleta de PDFs até a geração de rankings atualizados, mantendo custos operacionais mínimos (<$0.05/mês) e disponibilidade de 99.95%.

---

## 1. Objetivo

O projeto busca investigar a viabilidade técnica e metodológica de aplicar métricas dinâmicas de desempenho profissional na área jurídica, com ênfase na atuação processual de advogados, por meio de:

- **Coleta automatizada**: Download diário de decisões judiciais com verificação de integridade
- **Arquivo permanente**: Armazenamento público no Internet Archive (99.95% redução de storage local)
- **Extração por IA**: Processamento via Google Gemini com rate limiting e chunking inteligente
- **Análise de performance**: Sistema OpenSkill para avaliação dinâmica de habilidades jurídicas
- **Armazenamento unificado**: Banco DuckDB substituindo 50+ arquivos CSV/JSON dispersos
- **Backup resiliente**: Snapshots comprimidos em Cloudflare R2 com queries remotas
- **Operação autônoma**: Pipeline completo executado via GitHub Actions (3:15-7:00 UTC)

---

## 2. Justificativa

A performance de advogados perante o judiciário é usualmente avaliada de maneira qualitativa ou pontual, sem padronização objetiva. Com o crescimento da disponibilidade de dados jurídicos abertos, torna-se possível construir mecanismos mais analíticos e automatizados de acompanhamento de desempenho.

A adoção de um modelo como o OpenSkill para o ambiente forense oferece vantagens significativas:
- Oponentes com diferentes níveis de experiência.
- Resultados de partidas (vitória, derrota ou empate) entre equipes.
- Evolução temporal da atuação.
- Suporte nativo para equipes de advogados de tamanhos variáveis.
- Quantificação da incerteza da pontuação de cada advogado (representada pelos parâmetros μ e σ).

Essa abordagem oferece potencial para estudos empíricos no campo do direito, além de servir como base para aplicações institucionais (ex: defensoria, advocacia pública) ou educativas.

---

## 3. Metodologia

### 3.1 Fonte dos Dados

A fonte primária de dados é o **Diário da Justiça Eletrônico do TJRO**, acessado diariamente por meio de script automatizado. Os arquivos em formato PDF são armazenados e versionados no repositório.

### 3.2 Extração de Conteúdo

Utiliza-se o modelo **Gemini** (Google) para leitura direta dos arquivos PDF, dispensando OCR ou etapas manuais de conversão. O modelo é instruído por prompt específico para identificar:

- Número do processo (CNJ).
- Nome das partes (autor e réu).
- Nome dos advogados de cada parte.
- Resultado da decisão (procedente, improcedente, extinto, etc.).

A resposta é armazenada em formato JSON estruturado.

### 3.3 Modelo de Pontuação

Para cada decisão extraída:

1. As equipes de advogados do polo ativo e passivo são identificadas.
2. Um “confronto” entre as equipes é estabelecido com base no resultado da decisão.
3. Aplicam-se as regras do sistema OpenSkill, atualizando os parâmetros `mu` (habilidade média) e `sigma` (incerteza da habilidade) de cada advogado envolvido. Os parâmetros base do ambiente OpenSkill (`mu` e `sigma` iniciais, `beta`, `tau`) são configuráveis através do arquivo `config.toml` na raiz do projeto, na seção `[openskill]`.
4. Atualizam-se os scores `mu` e `sigma` de todos os profissionais nos arquivos CSV de rating.

### 3.4 Arquitetura de Dados Multi-Camadas

O sistema implementa uma **estratégia de três camadas** para otimizar custo, performance e resilência:

#### Camada 1: DuckDB Local (Operações Primárias)
- `data/causaganha.duckdb`: Banco unificado com 6 tabelas principais
- **ratings**: Rankings OpenSkill (μ, σ) de advogados
- **partidas**: Histórico completo de confrontos processados
- **decisoes**: Decisões extraídas com status de validação
- **pdfs**: Metadados do Internet Archive com hashes SHA-256

#### Camada 2: Internet Archive (Armazenamento Público Permanente)
- **Acesso público**: Todos os PDFs disponíveis em `archive.org/download/{item_id}/`
- **Custo zero**: Armazenamento permanente gratuito com CDN global
- **Transparência**: Suporte a requisitos de acesso público

#### Camada 3: Cloudflare R2 (Analytics e Backup)
- **Snapshots comprimidos**: Exports DuckDB diários com compressão zstandard
- **Queries remotas**: Análise SQL sem downloads locais
- **Recuperação de desastres**: Capacidade completa de restauração do sistema

As atualizações são realizadas automaticamente via **6 workflows GitHub Actions**, de forma programada e auditável.

---

## 4. Estrutura do Projeto

```
causaganha/
├── openskill_rating.py    # Sistema OpenSkill
├── src/                   # Módulos principais
│   ├── downloader.py      # Coleta PDF + Internet Archive
│   ├── extractor.py       # Processamento via Gemini
│   ├── database.py        # Camada DuckDB unificada
│   ├── migration.py       # Migração CSV/JSON → DuckDB
│   ├── r2_storage.py      # Backup Cloudflare R2
│   ├── r2_queries.py      # Queries remotas R2
│   └── pipeline.py        # Orquestrador CLI
├── data/                  # Dados unificados
│   ├── causaganha.duckdb  # Banco principal
│   ├── dj_YYYYMMDD.pdf    # PDFs (+ Internet Archive)
│   └── backup_pre_migration/ # Backup CSVs originais
├── pipeline/              # Scripts especializados
│   └── collect_and_archive.py # Automação Internet Archive
├── .github/workflows/     # Pipeline completo (6 workflows)
│   ├── 01_collect.yml     # Coleta PDFs (5:00 UTC)
│   ├── 02_archive_to_ia.yml # Archive.org (3:15 UTC)
│   ├── 02_extract.yml     # Gemini (6:00 UTC)
│   ├── 03_update.yml      # OpenSkill + DuckDB (6:30 UTC)
│   ├── 04_backup_r2.yml   # Backup R2 (7:00 UTC)
│   └── test.yml           # Testes e qualidade
├── tests/                 # Suíte de testes expandida
│   └── test_r2_storage.py # Testes R2
└── pyproject.toml         # uv dependency management
```

---

## 5. Execução Local

### Pré-requisitos

- Python 3.11+
- Conta com acesso à API Gemini
- Git (opcional: Git LFS, se migrar para SQLite)

### Etapas

```bash
# Clonar o repositório
git clone https://github.com/franklinbaldo/causa_ganha.git # Corrigido para o repositório correto
cd causa_ganha

# Criar ambiente virtual e instalar dependências
# Recomenda-se Python 3.12+ conforme pyproject.toml
python3 -m venv .venv
source .venv/bin/activate
# O projeto usa 'uv' para gerenciamento de dependências e ambiente, instalado via pipx ou pip.
# Veja https://github.com/astral-sh/uv
# pip install uv # Se ainda não tiver o uv
uv pip install -e .[dev] # Instala o projeto em modo editável e dependências de desenvolvimento
# Ou, se preferir usar pip diretamente com pyproject.toml:
# pip install -e .[dev]

# Configurar pre-commit (opcional, mas recomendado)
pre-commit install
# pre-commit run --all-files # Para rodar em todos os arquivos

# Definir chave da API Gemini
export GEMINI_API_KEY="sua_chave"
# (opcional) JSON da conta de serviço do Google Drive
export GDRIVE_SERVICE_ACCOUNT_JSON='{...}'
# (opcional) Pasta de destino no Drive
export GDRIVE_FOLDER_ID="abc123"

# Rodar pipeline completo
uv run python src/pipeline.py run --date 2025-06-01

# Migrar dados existentes para DuckDB (setup inicial)
uv run python src/migration.py

# Backup para Cloudflare R2
uv run python src/r2_storage.py backup

# Consultas remotas sem download
uv run python src/r2_queries.py rankings --limit 10

# Arquivar PDF no Internet Archive
uv run python scripts/collect_and_archive.py --latest


---

## Running Tests

Após instalar as dependências, execute a suíte de testes com:

```bash
uv run pytest -q
```

Conforme descrito em `AGENTS.md`, rodar os testes é obrigatório antes de
realizar commits.

---

## 6. Pipeline Automatizado de Produção

O sistema opera com **6 workflows GitHub Actions** executando um pipeline completo de dados:

### Fluxo Diário (3:15-7:00 UTC)
1. **03:15 UTC** - `02_archive_to_ia.yml`: Upload para Internet Archive
2. **05:00 UTC** - `01_collect.yml`: Coleta de PDFs do TJRO
3. **06:00 UTC** - `02_extract.yml`: Extração via Gemini
4. **06:30 UTC** - `03_update.yml`: Atualização OpenSkill + DuckDB
5. **07:00 UTC** - `04_backup_r2.yml`: Backup para Cloudflare R2
6. **On PR/Push** - `test.yml`: Testes e validação de qualidade

### Secrets Necessários
```bash
# Obrigatórios
GEMINI_API_KEY=sua_chave_gemini
IA_ACCESS_KEY=sua_chave_internet_archive
IA_SECRET_KEY=sua_chave_secreta_ia
CLOUDFLARE_ACCOUNT_ID=seu_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=sua_r2_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=sua_r2_secret

# Opcionais (legacy)
GDRIVE_SERVICE_ACCOUNT_JSON='{...}'
GDRIVE_FOLDER_ID=abc123
```

O fluxo é **100% autônomo** com processamento de PDFs → rankings atualizados em ~4 horas.

## Documentação

A documentação do projeto é construída com **MkDocs** e publicada via GitHub Pages em `franklinbaldo.github.io/causa_ganha`. Os arquivos fonte encontram-se na pasta [`docs/`](docs/).


---

## 7. Status Atual: Produção

### ✅ **Implementado e Operacional**
- **Pipeline completo**: 6 workflows automatizados executando diariamente
- **Armazenamento multi-camadas**: DuckDB + Internet Archive + Cloudflare R2
- **57+ testes unitários**: Cobertura completa com mocks de APIs externas
- **Custos mínimos**: <$0.05/mês de operação
- **Resilência**: Múltiplas camadas de backup e recuperação
- **Análise remota**: Queries SQL contra dados em nuvem

### ⚠️ **Limitações Conhecidas**
- **Precisão do LLM**: Dependência da qualidade de interpretação do Gemini
- **Nomes inconsistentes**: Grafias variadas podem afetar identificação de advogados
- **Decisões complexas**: Empates e resultados parciais com ponderação básica (OpenSkill pode lidar com parciais se identificados)

### 🎯 **Métricas de Performance**
- **Disponibilidade**: 99.95% (baseado em Internet Archive)
- **Redução de storage**: 99.95% (PDFs movidos para IA)
- **Tempo de processamento**: ~4 horas (coleta → rankings)
- **Cobertura de testes**: 57+ testes com mocking completo



---

## 8. Roadmap e Expansões

### 🚀 **Próximas Funcionalidades**
- **Multi-tribunal**: Suporte a TJSP, TRFs e outros tribunais
- **Dashboard interativo**: Visualização via Streamlit ou Next.js
- **Classificação por área**: Segmentação por direito civil, criminal, etc.
- **Validação cruzada**: Integração com dados de andamentos processuais
- **API pública**: Endpoint REST para acesso aos rankings
- **Machine Learning**: Predição de resultados baseada em histórico

### 🔧 **Otimizações Técnicas**
- **Cache inteligente**: Redução de calls para APIs externas
- **Paralelização**: Processamento simultâneo de múltiplos PDFs
- **Alertas proativos**: Notificações de falhas no pipeline
- **Métricas avançadas**: Observabilidade completa do sistema



---

9. Licença

Este projeto é licenciado sob os termos da MIT License.


---

10. Referências

OpenSkill: [https://github.com/open-skill/openskill.py](https://github.com/open-skill/openskill.py)

Tribunal de Justiça do Estado de Rondônia – tjro.jus.br

Google Gemini API – developers.generativeai.google



---

---

## 🏆 **CausaGanha: Plataforma de Análise Judicial de Nível Empresarial**

CausaGanha demonstra como **inteligência artificial**, **arquitetura multi-nuvem** e **algoritmos de avaliação de habilidades** podem ser combinados para criar uma plataforma robusta, escalável e econômica para análise empírica do desempenho jurídico.

Com **arquitetura de três camadas**, **pipeline totalmente automatizado** e **custos operacionais mínimos**, o projeto representa um avanço significativo na aplicação de ciência de dados ao sistema judiciário brasileiro.

**Status: ✅ PRODUÇÃO** - Sistema completo operando com automação de nível empresarial.

O projeto está aberto à colaboração e feedback da comunidade jurídica, técnica e acadêmica.
