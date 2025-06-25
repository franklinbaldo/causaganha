# CausaGanha

[![Update TrueSkill Ratings](https://img.shields.io/github/actions/workflow/status/franklinbaldo/causa_ganha/03_update.yml?label=update-trueskill)](https://github.com/franklinbaldo/causa_ganha/actions/workflows/03_update.yml)

**CausaGanha** é uma plataforma automatizada de extração e análise de decisões judiciais que aplica o sistema de pontuação **TrueSkill** — desenvolvido pela Microsoft Research para jogos com múltiplos jogadores e equipes — à atuação de advogados em processos judiciais. A proposta consiste em construir um modelo dinâmico e transparente de avaliação de desempenho com base em decisões publicadas diariamente no Diário de Justiça do Tribunal de Justiça de Rondônia (TJRO).

Utilizando modelos de linguagem de grande escala (LLMs), especificamente o **Gemini** da Google, o sistema interpreta diretamente os arquivos em formato PDF, identifica os elementos relevantes de cada decisão (partes, representantes e resultado), e atualiza o histórico e o escore de cada advogado envolvido.

---

## 1. Objetivo

O projeto busca investigar a viabilidade técnica e metodológica de aplicar métricas dinâmicas de desempenho profissional na área jurídica, com ênfase na atuação processual de advogados, por meio de:

- Extração automatizada de decisões judiciais publicadas em fontes públicas oficiais.
- Análise textual assistida por inteligência artificial para identificar autores, réus, representantes e desfechos.
- Aplicação do algoritmo de pontuação TrueSkill, que lida nativamente com equipes e incerteza, ao contexto jurídico-contencioso.
- Atualização contínua de arquivos CSV contendo histórico de decisões e rankings.

---

## 2. Justificativa

A performance de advogados perante o judiciário é usualmente avaliada de maneira qualitativa ou pontual, sem padronização objetiva. Com o crescimento da disponibilidade de dados jurídicos abertos, torna-se possível construir mecanismos mais analíticos e automatizados de acompanhamento de desempenho.

A adoção do modelo TrueSkill para o ambiente forense oferece vantagens significativas:
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
3. Aplicam-se as regras do sistema TrueSkill, atualizando os parâmetros `mu` (habilidade média) e `sigma` (incerteza da habilidade) de cada advogado envolvido. Os parâmetros base do ambiente TrueSkill (`mu` e `sigma` iniciais, `beta`, `tau` e `draw_probability`) são configuráveis através do arquivo `config.toml` na raiz do projeto.
4. Atualizam-se os scores `mu` e `sigma` de todos os profissionais nos arquivos CSV de rating.

### 3.4 Persistência e Versionamento

Os dados são armazenados em arquivos `.csv` rastreáveis no próprio repositório:

- `data/ratings.csv`: ranking atual dos advogados (contendo `mu`, `sigma` e `total_partidas`).
- `data/partidas.csv`: histórico completo das decisões processadas.
- `config.toml`: arquivo de configuração para os parâmetros do ambiente TrueSkill.

As atualizações são realizadas automaticamente via **GitHub Actions**, de forma programada e auditável.

---

## 4. Estrutura do Projeto

causaganha/ ├── core/                  # Módulos principais │   ├── downloader.py      # Baixa PDF do diário │   ├── extractor.py       # Envia PDF ao Gemini │   ├── trueskill_rating.py # Modelo de pontuação TrueSkill │   └── pipeline.py        # Orquestrador CLI │ ├── data/                  # Dados coletados e processados │   ├── diarios/           # PDFs originais │   ├── json/              # Decisões extraídas │   ├── ratings.csv        # Ranking TrueSkill (mu, sigma) │   └── partidas.csv       # Confrontos processados │ ├── .github/workflows/     # Integração contínua │   ├── 01_collect.yml │   ├── 02_extract.yml │   └── 03_update.yml │ ├── requirements.txt └── README.md

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
python -m causaganha.core.pipeline run --date 2025-06-01


---

## Running Tests

Após instalar as dependências, execute a suíte de testes com:

```bash
pytest -q
```

Conforme descrito em `AGENTS.md`, rodar os testes é obrigatório antes de
realizar commits.

---

6. Agendamento Automatizado

O repositório possui workflows GitHub Actions com agendamento diário (cron) para:

Baixar o Diário da Justiça

Extrair as decisões via LLM

Atualizar pontuações e salvar arquivos CSV

Certifique-se de definir o secret `GEMINI_API_KEY` no repositório para que o passo de extração funcione corretamente.
Para que os PDFs sejam enviados ao Google Drive, configure também os secrets `GDRIVE_SERVICE_ACCOUNT_JSON` e `GDRIVE_FOLDER_ID`.


O fluxo é 100% autônomo e auditável via histórico de commits.

## Documentação

A documentação do projeto é construída com **MkDocs** e publicada via GitHub Pages em `franklinbaldo.github.io/causa_ganha`. Os arquivos fonte encontram-se na pasta [`docs/`](docs/).


---

7. Limitações Atuais

O sistema depende da precisão do modelo LLM para interpretar corretamente os PDFs (pode haver ruído).

Empates ou decisões parciais ainda não possuem ponderação refinada.

A extração de nomes de advogados pode ser afetada por grafias inconsistentes ou ausência de registro.



---

8. Expansão Futura

Suporte a múltiplos tribunais e fontes (ex: TJSP, TRFs).


Visualização interativa dos rankings (via Streamlit ou Next.js).

Classificação por área do direito ou tipo de processo.

Validação cruzada com dados de andamentos processuais.



---

9. Licença

Este projeto é licenciado sob os termos da MIT License.


---

10. Referências

Herbrich, R., Minka, T., & Graepel, T. (2007). TrueSkill(TM): A Bayesian Skill Rating System. *Advances in Neural Information Processing Systems 19 (NIPS 2006)*. (Disponível em: [https://papers.nips.cc/paper/2006/hash/511FBC93A5B8F9A00336C46A844A6562-Abstract.html](https://papers.nips.cc/paper/2006/hash/511FBC93A5B8F9A00336C46A844A6562-Abstract.html))

Microsoft Research. TrueSkill Rating System. (Disponível em: [https://www.microsoft.com/en-us/research/project/trueskill-rating-system/](https://www.microsoft.com/en-us/research/project/trueskill-rating-system/))

Tribunal de Justiça do Estado de Rondônia – tjro.jus.br

Google Gemini API – developers.generativeai.google



---

CausaGanha é uma proposta de aproximação entre o direito e a ciência de dados, com o objetivo de fomentar novas formas de análise empírica da atuação processual. O projeto está aberto à colaboração e feedback da comunidade jurídica, técnica e acadêmica.

