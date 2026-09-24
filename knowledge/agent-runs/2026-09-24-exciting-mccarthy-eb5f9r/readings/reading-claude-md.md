---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-eb5f9r-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta apenas djen_backup (motor de sincronizacao DJEN/Internet Archive) e o pipeline .qmd do frontend como dominios formais; a linhagem do corpus do segmentador (#1050, src/segmenter_dataset, scripts/*segmenter*, data/segmenter*) fica fora do mapa de arquivos, mas continua sob as mesmas regras gerais de estilo (ruff estrito, TRY300/301/401, proibicao de except Exception amplo fora do bulkhead ADR-0011, Python 3.12+, uv run ruff check/format --check + uv run pytest -q antes de commitar). Esta rodada nao planeja tocar djen_backup nem web/, entao as secoes de contrato de manifesto e boundary CSS Panda nao se aplicam diretamente."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve dois runtimes formais: `src/djen_backup` (motor de
sincronizacao DJEN/Internet Archive, `sync-manifest.parquet` como fonte
de verdade unica, distincao critica `djen_raw` transporte vs
`djen_status` derivado, disciplina sobre 403 vs 404/400/200-sem-URL) e
`web/src/queries/*.qmd` (contrato de dados do frontend). O trabalho
desta rodada (revisar/mesclar PRs paradas da linhagem do segmentador,
#1050) vive fora desse mapa, em `src/segmenter_dataset`/
`scripts/*segmenter*`/`data/segmenter*`, mas segue as regras gerais:
`uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`
antes de qualquer commit; TRY300/TRY301/TRY401; proibicao de `except
Exception` amplo fora de bulkhead documentado por ADR. Nenhuma mudanca
planejada em `djen_backup` ou `web` nesta rodada.

Achado adicional relevante para a escolha de trabalho: `.claude/
hourly-loop.md` (fora do CLAUDE.md, mas lido como parte da leitura de
conhecimento OKF/knowledge desta rodada -- ver reading-okf) declara que
o loop horario do projeto agora e operado exclusivamente pelo runtime
Wisk e instrui a nao criar novos `AgentRun` "no loop horario". O prompt
armazenado desta sessao agendada, porem, instrui explicitamente o fluxo
`AgentRun`/scaffold classico. Ver decision correspondente sobre como
esta tensao foi resolvida nesta rodada.
