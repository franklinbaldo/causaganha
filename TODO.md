TODO – CausaGanha

Este documento descreve, em etapas sequenciais, as tarefas necessárias para transformar o README.md em um protótipo funcional e reprodutível do projeto CausaGanha.

> Convenções
✓ = concluído ⌛ = em progresso □ = pendente 🛈 = observação ou link




---

Milestone 0 – Preparação do Repositório

Status	Tarefa	Detalhes

✓	Criar estrutura de pastas	causaganha/, legalelo/, data/diarios, data/json
✓	Configurar ambiente Python	pyproject.toml ou requirements.txt (Python 3.11)
✓	Habilitar GitHub Actions	Pasta .github/workflows/ vazia inicialmente
✓	Definir código de conduta & licença	Arquivo LICENSE (MIT) e CODE_OF_CONDUCT.md
✓	Adicionar templates de issue/PR	Boa governança do OSS



---

Milestone 1 – Coleta Diária de PDFs

Status	Tarefa	Detalhes

✓	downloader.py	Função fetch_tjro_pdf(date) → Path
✓	Log & versionamento	Nomear arquivos dj_{YYYY‑MM‑DD}.pdf em data/diarios/
✓	Workflow 01_collect.yml	Agendamento cron diário (05:00 UTC) + upload como artefato
✓	Teste local	Executar python -m legalelo.downloader --date 2025‑06‑01



---

Milestone 2 – Extração com Gemini

Status	Tarefa	Detalhes

✓	extractor.py	Classe GeminiExtractor com prompt parametrizado
✓	Formato de saída	JSON por decisão em data/json/{processo}.json
✓	Workflow 02_extract.yml	Gatilho: sucesso de 01_collect.yml; matriz paralela por página
✓	Cache de tokenização	Memória local para não reprocessar PDFs idênticos



---

Milestone 3 – Modelo Elo

Status	Tarefa	Detalhes

✓	elo.py	Funções expected(r_a,r_b) e update(r_a,r_b,score,k) (K = 16)
✓	ratings.csv & partidas.csv	Schema definido no README
✓	Validação	Testes unitários com cenários simples (vitória, derrota, empate)



---

Milestone 4 – Orquestração CLI

Status	Tarefa	Detalhes

□	pipeline.py	Comandos collect, extract, update, run (orquestra tudo)
□	CLI via argparse	Flags --date, --dry-run, --verbose
□	Logging estruturado	logging JSON‑friendly (nível INFO)



---

Milestone 5 – Integração Contínua Completa

Status	Tarefa	Detalhes

□	Workflow 03_update.yml	Roda pipeline run e commit CSVs atualizados
□	Secrets	GEMINI_API_KEY adicionado no repositório ⇢ Settings → Secrets
□	Badge de status	README mostra último workflow (shields.io)



---

Milestone 6 – Qualidade & Testes

Status	Tarefa	Detalhes

□	Lint	ruff + pre‑commit
□	CI Test	pytest no GitHub Actions
□	Cobertura	coverage.xml + Codecov badge



---

Milestone 7 – Distribuição e Documentação

Status	Tarefa	Detalhes

□	Docs via MkDocs	Publicar em GitHub Pages (/docs)
□	Tutorial rápido	Como rodar o projeto em 5 min
□	FAQ & Limitações	Seção dedicada



---

Milestone 8 – Roadmap de Expansão (opcional)

□ Suporte a múltiplos tribunais (parametrizar downloader)

□ Migrar de CSV para SQLite/PostgreSQL (SQLModel / Supabase)

□ Dashboard interativo (Streamlit / Next.js)

□ Ajustar fator K adaptativo com cross‑validation

□ Classificação por área do direito



---

Referência Rápida de Scripts

# Executar apenas coleta
python -m legalelo.pipeline collect --date 2025-06-01

# Executar pipeline completo (coleta → extração → Elo)
python -m legalelo.pipeline run --date 2025-06-01


---

Próximos Passos Imediatos

1. Configurar o segredo GEMINI_API_KEY no repositório.


2. Implementar downloader.py com URL estática de teste.


3. Validar extração em lote pequeno (<= 10 páginas) para calibrar prompt.





Criei um TODO.md detalhado, já estruturado em marcos (Milestones) e tarefas com check-boxes, cobrindo desde a configuração inicial do repositório até qualidade de código, CI e roadmap de expansão. Sinta-se à vontade para revisar e marcar o que for avançando — e diga se quiser ajustes ou aprofundar algum item!

