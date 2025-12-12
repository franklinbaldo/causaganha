# CausaGanha

> 🤖 **Para Assistentes de IA**: Consulte **`CLAUDE.md`** para instruções completas de desenvolvimento, incluindo abordagem plan-first, coordenação MASTERPLAN, e guidelines específicas para agentes de código.

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![Breaking Changes](https://img.shields.io/badge/breaking_changes-expected-red?style=for-the-badge)
![No Backwards Compatibility](https://img.shields.io/badge/backwards_compatibility-none-critical?style=for-the-badge)

[![Update OpenSkill Ratings](https://img.shields.io/github/actions/workflow/status/franklinbaldo/causa_ganha/03_update.yml?label=update-openskill)](https://github.com/franklinbaldo/causa_ganha/actions/workflows/03_update.yml)

> ⚠️ **SOFTWARE ALPHA**: Este projeto está em desenvolvimento ativo com mudanças radicais frequentes. APIs, schemas de banco de dados e funcionalidades principais podem mudar sem aviso ou compatibilidade com versões anteriores. Use por sua conta e risco em ambientes de produção.

## 🚀 Transição para v2 em Andamento

**O CausaGanha está se preparando para uma grande refatoração v2** que integrará a API de Comunicações do PJe e substituirá web scraping por coleta de metadados estruturados via API.

### Principais Mudanças da v2

- **Coleta de Metadados**: Web scraping → API de Comunicações PJe (JSON estruturado)
- **Operações de Dados**: pandas → Ibis (10-100x mais rápido)
- **Integração LLM**: SDK direto Gemini → Pydantic AI (agnóstico de provedor)
- **Cobertura**: Apenas TJRO → 90+ tribunais com suporte PJe

### Status do Desenvolvimento v2

- ✅ **Fase 0 (Atual)**: Preparação do repositório e estrutura de diretórios v2
- 🔄 **Fase 1-3 (Semanas 1-3)**: Implementação v2 baseada em TDD em paralelo com v1
- ⏳ **Fase 4-6 (Semanas 4-6)**: Integração, produção paralela, migração
- ⏳ **Fase 7-9 (Semanas 7-9)**: Expansão para novos tribunais, limpeza

📖 **Documentação Completa**: Consulte `/causaganha-v2-plan-from-scratch.md` para o plano completo de implementação.

---

**CausaGanha** é uma **plataforma de análise judicial distribuída em estágio alpha** que combina inteligência artificial, processamento assíncrono e algoritmos de avaliação de habilidades para criar um sistema automatizado de avaliação de desempenho jurídico. Utilizando o sistema **OpenSkill**, uma alternativa de código aberto, a plataforma analisa decisões judiciais do Tribunal de Justiça de Rondônia (TJRO) para gerar rankings dinâmicos e transparentes de advogados.

## Características Principais

- **🤖 Análise por IA**: Extração automatizada via Google Gemini
- **📊 Sistema OpenSkill**: Avaliação dinâmica de performance jurídica
- **🌐 Distribuído**: DuckDB compartilhado via Internet Archive
- **⚡ Assíncrono**: Processamento concorrente de milhares de diários
- **🔄 Automatizado**: Workflows GitHub Actions para operação autônoma

## Instalação Rápida

```bash
# Instalar uv (gerenciador de dependências)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clonar e configurar
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha
uv venv && source .venv/bin/activate
uv sync --dev && uv pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves API
```

## Uso Básico

```bash
# Configurar banco de dados
uv run --env-file .env causaganha db migrate

# Adicionar URLs para processamento
uv run --env-file .env causaganha queue --from-csv diarios.csv

# Sincronizar banco de dados com a IA
uv run --env-file .env causaganha db sync

# Executar pipeline completo
uv run --env-file .env causaganha pipeline run --date 2025-06-24

# Monitorar progresso
uv run --env-file .env causaganha stats

# Comandos individuais
uv run --env-file .env causaganha archive --limit 10
uv run --env-file .env causaganha analyze --limit 5
uv run --env-file .env causaganha score
```

## Comandos Principais

| Comando        | Descrição                                    |
| -------------- | -------------------------------------------- |
| `queue`        | Adiciona documentos à fila de processamento  |
| `archive`      | Download e armazenamento no Internet Archive |
| `analyze`      | Extração de informações via LLM              |
| `score`        | Geração de rankings OpenSkill                |
| `pipeline run` | Executa pipeline assíncrono                  |
| `stats`        | Estatísticas e progresso                     |
| `db sync`      | Sincroniza banco de dados                    |
| `db`           | Operações de banco de dados                  |

### Exemplos de CLI

```bash
causaganha db sync
causaganha pipeline run --date 2025-06-24
```

### Ajuda da CLI

```bash
causaganha --help             # visão geral dos comandos
causaganha db --help          # opções do grupo de banco
causaganha pipeline run --help # parâmetros do pipeline
```

## Variáveis de Ambiente

```bash
GEMINI_API_KEY=sua_chave_gemini    # Obrigatório para extração
IA_ACCESS_KEY=sua_chave_ia         # Obrigatório para Internet Archive
IA_SECRET_KEY=sua_chave_secreta_ia # Obrigatório para Internet Archive
```

## Testes

```bash
uv run pytest -q
```

### Uso opcional no VSCode

Para quem utiliza o VSCode, o diretório `.vscode/` contém configurações que:

- Definem `.venv/bin/python` como interpretador padrão;
- Ativam o linter **Ruff**;
- Configuram a descoberta de testes em `tests/`.

### Ambiente de desenvolvimento com Docker Compose

Para quem prefere um ambiente isolado em contêiner:

```bash
./scripts/setup_dev.sh          # cria `.venv` e instala dependências
./scripts/dev/install_precommit_hooks.sh  # configura hooks do pre-commit (Ruff)
./scripts/dev/docker_shell.sh   # abre um shell dentro do contêiner
```

O serviço `analytics` pode ser executado via Docker Compose, e um painel Grafana
é disponibilizado em `http://localhost:3000` ao rodar:

```bash
docker compose up grafana
```

## Documentação

Para gerar a documentação HTML localmente utilize o Sphinx:

```bash
sphinx-build -b html docs/api docs/_build
```

Para conveniência, você também pode rodar:

```bash
make -C docs/api html
```

Consulte os notebooks em `docs/tutorials/` para exemplos de uso do pipeline.
Documentação das rotinas de analytics está disponível em `docs/api/analytics.rst`.
O tutorial `tribunal_adapter.ipynb` detalha a criação de adaptadores.

## Status do Projeto

**Status: 🔶 ALPHA DISTRIBUÍDO** - Sistema experimental operando com automação avançada, mudanças radicais esperadas.

### ⚠️ Aviso de Status Alpha

**CausaGanha é SOFTWARE ALPHA** com as seguintes implicações:

- **Mudanças Radicais**: APIs principais, comandos CLI e schemas de banco podem mudar sem aviso
- **Sem Compatibilidade**: Atualizações podem exigir migração completa de dados ou reinstalação
- **Recursos Experimentais**: Novas funcionalidades podem ser adicionadas, modificadas ou removidas rapidamente

**Use em produção por sua conta e risco.** Considere este software experimental e espere adaptar-se a mudanças radicais.

## Licença

Este projeto é licenciado sob os termos da MIT License.

---

O projeto está aberto à colaboração e feedback da comunidade jurídica, técnica e acadêmica.

## Exemplos

Veja scripts de exemplo em [docs/examples](docs/examples) para demonstrações de processamento de dados e tratamento de erros.
O script [diario_processing_example.py](docs/examples/diario_processing_example.py) mostra como executar o pipeline para diferentes tribunais usando a opção `--tribunal`.
Esses exemplos utilizam os dados fictícios em `tests/mock_data` para facilitar testes locais.
