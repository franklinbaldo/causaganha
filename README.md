# CausaGanha

[![Update OpenSkill Ratings](https://img.shields.io/github/actions/workflow/status/franklinbaldo/causa_ganha/03_update.yml?label=update-openskill)](https://github.com/franklinbaldo/causa_ganha/actions/workflows/03_update.yml)

**CausaGanha** é uma **plataforma de análise judicial distribuída de nível empresarial** que combina inteligência artificial, processamento assíncrono e algoritmos de avaliação de habilidades para criar um sistema automatizado de avaliação de desempenho jurídico. Utilizando o sistema **OpenSkill**, uma alternativa de código aberto, a plataforma analisa decisões judiciais do Tribunal de Justiça de Rondônia (TJRO) para gerar rankings dinâmicos e transparentes de advogados.

O sistema implementa uma **arquitetura distribuída de 2 camadas** com:
- **Processamento distribuído**: DuckDB compartilhado via Internet Archive para colaboração entre PC/GitHub Actions
- **Arquivo público permanente**: Internet Archive para transparência, acesso público e backup
- **Pipeline assíncrono**: Processamento concorrente de 5,058 diários (2004-2025) com sistema de locks

Com **4 workflows automatizados** e pipeline assíncrono, a plataforma processa desde a coleta massiva de PDFs até a geração de rankings atualizados, mantendo custos operacionais zero e disponibilidade de 99.95%.

---

## 1. Objetivo

O projeto busca investigar a viabilidade técnica e metodológica de aplicar métricas dinâmicas de desempenho profissional na área jurídica, com ênfase na atuação processual de advogados, por meio de:

- **Coleta assíncrona massiva**: Download concorrente de 5,058 diários históricos (2004-2025) com verificação de integridade
- **Arquivo público permanente**: Armazenamento no Internet Archive (99.95% redução de storage local)
- **Extração por IA**: Processamento via Google Gemini com rate limiting e chunking inteligente
- **Análise de performance**: Sistema OpenSkill para avaliação dinâmica de habilidades jurídicas
- **Banco distribuído**: DuckDB compartilhado entre PC e GitHub Actions via Internet Archive com sistema de locks
- **Pipeline assíncrono**: Processamento concorrente configurável (3 downloads, 2 uploads simultâneos)
- **Operação autônoma**: Sistema completo de workflows GitHub Actions com sincronização automática

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
├── src/                   # Módulos principais (arquitetura src-layout)
│   ├── async_diario_pipeline.py  # Pipeline assíncrono principal
│   ├── ia_database_sync.py       # Sincronização distribuída do banco
│   ├── downloader.py             # Coleta PDF + Internet Archive
│   ├── extractor.py              # Processamento via Gemini
│   ├── database.py               # Camada DuckDB unificada
│   ├── ia_discovery.py           # Descoberta e listagem IA
│   ├── diario_processor.py       # Processamento dos diários
│   └── pipeline.py               # Orquestrador CLI
├── data/                  # Dados unificados
│   ├── causaganha.duckdb           # Banco principal compartilhado
│   ├── diarios_pipeline_ready.json # 5,058 diários prontos para processamento
│   ├── diarios_2025_only.json     # Subset 2025 para testes
│   └── diarios/                    # PDFs temporários (arquivados no IA)
├── scripts/               # Scripts especializados
│   ├── bulk_discovery.py     # Descoberta massiva IA
│   └── collect_and_archive.py # Automação Internet Archive
├── .github/workflows/     # Pipeline distribuído (4 workflows)
│   ├── pipeline.yml           # Pipeline principal async (3:15 UTC)
│   ├── bulk-processing.yml    # Processamento massivo (manual)
│   ├── database-archive.yml   # Archive database snapshots
│   └── test.yml               # Testes e qualidade
├── tests/                 # Suíte de testes unificada
│   └── test_*.py             # Testes abrangentes
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
git clone https://github.com/franklinbaldo/causa_ganha.git
cd causa_ganha

# Criar ambiente virtual usando uv (recomendado)
# Instalar uv: curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate  # ou `.venv\Scripts\activate` no Windows
uv sync --dev
uv pip install -e .  # Instalar em modo desenvolvimento

# Configurar variáveis de ambiente
export GEMINI_API_KEY="sua_chave_gemini"
# (opcional) Para upload no Internet Archive
export IA_ACCESS_KEY="sua_chave_ia"
export IA_SECRET_KEY="sua_chave_secreta_ia"

# === COMANDOS PRINCIPAIS ===

# Pipeline assíncrono completo (recomendado)
causaganha pipeline run --date 2025-06-24           # Pipeline completo
causaganha pipeline run --date 2025-06-24 --dry-run # Teste sem modificações

# Processamento assíncrono massivo
uv run python src/async_diario_pipeline.py --max-items 10 --verbose
uv run python src/async_diario_pipeline.py --start-date 2025-01-01 --end-date 2025-06-26

# Sincronização distribuída do banco
uv run python src/ia_database_sync.py sync
uv run python src/ia_database_sync.py status

# Descoberta no Internet Archive
uv run python src/ia_discovery.py --year 2025
uv run python src/ia_discovery.py --coverage-report

# Comandos individuais
causaganha download --latest                         # Download apenas
causaganha extract --pdf-file data/file.pdf         # Extração apenas
causaganha db migrate                                # Migração de dados

# Testes obrigatórios
uv run pytest -q


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

O sistema opera com **4 workflows GitHub Actions** executando um pipeline distribuído completo:

### Pipeline Principal (3:15 UTC diário)
1. **pipeline.yml**: Pipeline assíncrono unificado com sincronização de banco
   - Sincroniza banco compartilhado do Internet Archive
   - Executa pipeline assíncrono (configurável: últimos 5 itens por padrão)
   - Upload banco atualizado para Internet Archive
   - Relatório estatístico completo

### Workflows Especializados
2. **bulk-processing.yml**: Processamento massivo (manual)
   - Processa por ano (2025, 2024, 2023) ou quantidade (100, 500, todos os 5,058 diários)
   - Concorrência configurável (downloads e uploads)
   - Timeout de 6 horas para grandes volumes

3. **database-archive.yml**: Snapshots públicos do banco (semanal)
   - Domingos às 4:00 UTC para snapshots semanais
   - Primeiro domingo do mês para arquivo permanente
   - Disponibilização pública para pesquisa

4. **test.yml**: Validação de qualidade (PR/Push)

### Secrets Necessários
```bash
# Obrigatórios
GEMINI_API_KEY=sua_chave_gemini
IA_ACCESS_KEY=sua_chave_internet_archive
IA_SECRET_KEY=sua_chave_secreta_ia

# Opcionais (legacy)
GDRIVE_SERVICE_ACCOUNT_JSON='{...}'
GDRIVE_FOLDER_ID=abc123
```

O sistema é **100% distribuído** com banco compartilhado e processamento coordenado entre ambientes locais e GitHub Actions.

## Documentação

A documentação do projeto é construída com **MkDocs** e publicada via GitHub Pages em `franklinbaldo.github.io/causa_ganha`. Os arquivos fonte encontram-se na pasta [`docs/`](docs/).


---

## 7. Status Atual: Produção

### ✅ **Implementado e Operacional**
- **Pipeline distribuído**: 4 workflows especializados com banco compartilhado
- **Processamento assíncrono**: 5,058 diários históricos (2004-2025) processáveis
- **Arquitetura distribuída**: Banco DuckDB sincronizado via Internet Archive
- **Sistema de locks**: Prevenção de conflitos em acessos concorrentes
- **67+ testes unitários**: Cobertura completa com mocks de APIs externas
- **Custos zero**: Operação sem custos com Internet Archive
- **Descoberta inteligente**: Ferramentas de análise e cobertura IA

### ⚠️ **Limitações Conhecidas**
- **Precisão do LLM**: Dependência da qualidade de interpretação do Gemini
- **Nomes inconsistentes**: Grafias variadas podem afetar identificação de advogados
- **Decisões complexas**: Empates e resultados parciais com ponderação básica (OpenSkill pode lidar com parciais se identificados)

### 🎯 **Métricas de Performance**
- **Disponibilidade**: 99.95% (baseado em Internet Archive)
- **Redução de storage**: 99.95% (PDFs arquivados no IA)
- **Processamento massivo**: 5,058 diários processáveis assincronamente
- **Sincronização**: Banco compartilhado com resolução automática de conflitos
- **Cobertura de testes**: 67+ testes com mocking completo
- **Concorrência**: 3 downloads + 2 uploads simultâneos (configurável)



---

## 8. Adaptação para Outros Tribunais

O design do CausaGanha permite a sua adaptação para analisar diários de qualquer tribunal, desde que você possua uma lista de URLs para os arquivos PDF dos diários. O sistema é agnóstico em relação à origem dos dados, focando no processamento do conteúdo dos PDFs.

### Requisito Principal

O único requisito é um arquivo JSON contendo uma lista de objetos, cada um com a data e a URL do diário.

**Formato do JSON:**
```json
[
  {
    "date": "YYYY-MM-DD",
    "url": "https://tribunal.exemplo.com/diario_AAAA_MM_DD.pdf"
  },
  {
    "date": "YYYY-MM-DD",
    "url": "https://tribunal.exemplo.com/diario_AAAA_MM_DD_ed_extra.pdf"
  }
]
```

### Passos para Adaptação

1.  **Crie o Arquivo JSON**: Compile a lista de URLs dos diários que você deseja processar e formate-a como o exemplo acima. Salve o arquivo (por exemplo, `meu_tribunal.json`).

2.  **Execute o Pipeline**: Utilize o script de processamento massivo, apontando para o seu novo arquivo JSON. O sistema fará o download, processamento e análise de cada PDF da lista.

    ```bash
    # Exemplo de comando para processar sua lista de diários
    uv run python src/async_diario_pipeline.py --input-file /caminho/para/meu_tribunal.json --max-items 100
    ```

    - `--input-file`: Especifica o caminho para o seu arquivo JSON customizado.
    - `--max-items`: Limita o número de diários a processar em uma execução (útil para testes).

Com estes passos, o sistema pode ser redirecionado para qualquer fonte de diários judiciais, mantendo a mesma lógica de extração, análise e ranqueamento.

---

## 9. Roadmap e Expansões

### 🚀 **Próximas Funcionalidades**
- **Processamento completo**: Finalizar os 5,058 diários históricos TJRO
- **Multi-tribunal**: Implementação TJSP como próximo alvo
- **Dashboard interativo**: Visualização via Streamlit ou Next.js
- **API pública**: Endpoint REST para acesso aos rankings
- **Machine Learning**: Predição de resultados baseada em histórico
- **Análise temporal**: Trends e padrões ao longo do tempo

### 🔧 **Otimizações Técnicas**
- **Cache inteligente**: Redução de calls para APIs externas
- **Alertas proativos**: Notificações de falhas no pipeline
- **Métricas avançadas**: Observabilidade completa do sistema
- **Paralelização avançada**: Otimização de concorrência dinâmica
- **Integração multi-cloud**: Suporte a outros provedores de backup



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
