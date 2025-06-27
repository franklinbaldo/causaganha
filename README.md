# CausaGanha

> 🤖 **Para Assistentes de IA**: Consulte **`CLAUDE.md`** para instruções completas de desenvolvimento, incluindo abordagem plan-first, coordenação MASTERPLAN, e guidelines específicas para agentes de código.

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![Breaking Changes](https://img.shields.io/badge/breaking_changes-expected-red?style=for-the-badge)
![No Backwards Compatibility](https://img.shields.io/badge/backwards_compatibility-none-critical?style=for-the-badge)

[![Update OpenSkill Ratings](https://img.shields.io/github/actions/workflow/status/franklinbaldo/causa_ganha/03_update.yml?label=update-openskill)](https://github.com/franklinbaldo/causa_ganha/actions/workflows/03_update.yml)

> ⚠️ **SOFTWARE ALPHA**: Este projeto está em desenvolvimento ativo com mudanças radicais frequentes. APIs, schemas de banco de dados e funcionalidades principais podem mudar sem aviso ou compatibilidade com versões anteriores. Use por sua conta e risco em ambientes de produção.

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

# Executar pipeline completo
uv run --env-file .env causaganha pipeline --from-csv diarios.csv

# Monitorar progresso
uv run --env-file .env causaganha stats

# Comandos individuais
uv run --env-file .env causaganha archive --limit 10
uv run --env-file .env causaganha analyze --limit 5
uv run --env-file .env causaganha score
```

## Comandos Principais

| Comando | Descrição |
|---------|-----------|
| `queue` | Adiciona documentos à fila de processamento |
| `archive` | Download e armazenamento no Internet Archive |
| `analyze` | Extração de informações via LLM |
| `score` | Geração de rankings OpenSkill |
| `pipeline` | Executa pipeline completo |
| `stats` | Estatísticas e progresso |
| `db` | Operações de banco de dados |

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