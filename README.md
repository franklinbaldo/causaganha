Claro. Aqui está o README.md reescrito com um tom mais sério e acadêmico, adequado para apresentação do projeto CausaGanha como uma iniciativa de pesquisa aplicada ou prova de conceito técnico-jurídico:


---

# CausaGanha

**CausaGanha** é uma plataforma automatizada de extração e análise de decisões judiciais que aplica o sistema de pontuação **Elo** — originalmente desenvolvido para classificar jogadores de xadrez — à atuação de advogados em processos judiciais. A proposta consiste em construir um modelo dinâmico e transparente de avaliação de desempenho com base em decisões publicadas diariamente no Diário de Justiça do Tribunal de Justiça de Rondônia (TJRO).

Utilizando modelos de linguagem de grande escala (LLMs), especificamente o **Gemini** da Google, o sistema interpreta diretamente os arquivos em formato PDF, identifica os elementos relevantes de cada decisão (partes, representantes e resultado), e atualiza o histórico e o escore de cada advogado envolvido.

---

## 1. Objetivo

O projeto busca investigar a viabilidade técnica e metodológica de aplicar métricas dinâmicas de desempenho profissional na área jurídica, com ênfase na atuação processual de advogados, por meio de:

- Extração automatizada de decisões judiciais publicadas em fontes públicas oficiais.
- Análise textual assistida por inteligência artificial para identificar autores, réus, representantes e desfechos.
- Aplicação de algoritmo de pontuação Elo adaptado ao contexto jurídico-contencioso.
- Atualização contínua de um banco de dados contendo histórico de decisões e rankings.

---

## 2. Justificativa

A performance de advogados perante o judiciário é usualmente avaliada de maneira qualitativa ou pontual, sem padronização objetiva. Com o crescimento da disponibilidade de dados jurídicos abertos, torna-se possível construir mecanismos mais analíticos e automatizados de acompanhamento de desempenho.

A adoção de um modelo Elo para o ambiente forense permite incorporar:
- Oponentes com diferentes níveis de experiência.
- Resultados binários ou neutros (ganhou, perdeu, extinto).
- Evolução temporal da atuação.
  
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

1. O advogado do autor e o advogado do réu são identificados.
2. Um “confronto” é estabelecido com base no resultado.
3. Aplicam-se regras do sistema Elo com fator K fixo (K = 16).
4. Atualiza-se a pontuação de ambos os profissionais no banco de dados.

### 3.4 Persistência e Versionamento

Os dados são armazenados em arquivos `.csv` rastreáveis no próprio repositório:

- `data/ratings.csv`: ranking atual dos advogados.
- `data/partidas.csv`: histórico completo das decisões processadas.

As atualizações são realizadas automaticamente via **GitHub Actions**, de forma programada e auditável.

---

## 4. Estrutura do Projeto

causaganha/ ├── legalelo/              # Módulos principais │   ├── downloader.py      # Baixa PDF do diário │   ├── extractor.py       # Envia PDF ao Gemini │   ├── elo.py             # Modelo de pontuação │   └── pipeline.py        # Orquestrador CLI │ ├── data/                  # Dados coletados e processados │   ├── diarios/           # PDFs originais │   ├── json/              # Decisões extraídas │   ├── ratings.csv        # Ranking Elo │   └── partidas.csv       # Confrontos processados │ ├── .github/workflows/     # Integração contínua │   ├── 01_collect.yml │   ├── 02_extract.yml │   └── 03_update.yml │ ├── requirements.txt └── README.md

---

## 5. Execução Local

### Pré-requisitos

- Python 3.11+
- Conta com acesso à API Gemini
- Git (opcional: Git LFS, se migrar para SQLite)

### Etapas

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/causaganha.git
cd causaganha

# Criar ambiente virtual e instalar dependências
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Definir chave da API Gemini
export GEMINI_API_KEY="sua_chave"

# Rodar pipeline completo
python -m legalelo.pipeline run --date 2025-06-01


---

6. Agendamento Automatizado

O repositório possui workflows GitHub Actions com agendamento diário (cron) para:

Baixar o Diário da Justiça

Extrair as decisões via LLM

Atualizar pontuações e salvar arquivos CSV


O fluxo é 100% autônomo e auditável via histórico de commits.


---

7. Limitações Atuais

O sistema depende da precisão do modelo LLM para interpretar corretamente os PDFs (pode haver ruído).

Empates ou decisões parciais ainda não possuem ponderação refinada.

A extração de nomes de advogados pode ser afetada por grafias inconsistentes ou ausência de registro.



---

8. Expansão Futura

Suporte a múltiplos tribunais e fontes (ex: TJSP, TRFs).

Integração com banco de dados relacional (PostgreSQL via Supabase).

Visualização interativa dos rankings (via Streamlit ou Next.js).

Classificação por área do direito ou tipo de processo.

Validação cruzada com dados de andamentos processuais.



---

9. Licença

Este projeto é licenciado sob os termos da MIT License.


---

10. Referências

ELO, A. E. (1978). The Rating of Chessplayers, Past and Present.

Tribunal de Justiça do Estado de Rondônia – tjro.jus.br

Google Gemini API – developers.generativeai.google



---

CausaGanha é uma proposta de aproximação entre o direito e a ciência de dados, com o objetivo de fomentar novas formas de análise empírica da atuação processual. O projeto está aberto à colaboração e feedback da comunidade jurídica, técnica e acadêmica.

Se quiser, posso gerar esse arquivo como `README.md` e montar os três arquivos iniciais do projeto em um repositório para começar. Deseja isso?

