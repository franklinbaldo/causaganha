# RFC 0008 — Testes e operacionalização de stj_acordaos e tjro_juris

- **Status:** Proposto (implementação neste PR)
- **Data:** 2026-07-07
- **Base:** `docs/planning/oportunidades-melhoria-2026-07.md` §4; RFCs 0002 e 0003

## 1. Problema

`src/stj_acordaos` (5 módulos) e `src/tjro_juris` (6 módulos) foram mesclados sem um único
teste — exatamente o código com maior chance de bug latente. Além disso, nenhum workflow
os invoca: sem cron, os datasets **não crescem**; os RFCs 0002/0003 estão implementados
mas não operacionalizados.

## 2. Testes (padrão de `tests/djen_backup/`)

Criar `tests/stj_acordaos/` e `tests/tjro_juris/`, priorizando o que é puro e barato de
testar, com `respx`/mocks para HTTP (nunca rede real):

### stj_acordaos
- `dedup.py`: chave de deduplicação, colisões, idempotência.
- `manifest.py`: parse/serialização, contagens, roundtrip.
- `client.py`: parse de payloads reais (fixtures pequenas), paginação, erros HTTP
  (403/timeout não viram "absent" — mesma disciplina do CLAUDE.md).
- `archive.py`: montagem de metadados/headers IA (`x-archive-meta-*`), sem upload real.

### tjro_juris
- `dedup.py`, `manifest.py`: idem.
- `client.py`/`crawler.py`: parse de HTML/JSON de fixtures, extração de campos
  (nr_processo, classe, órgão), paginação e condição de parada.

Critério: cada módulo com ≥1 teste significativo; caminhos de erro cobertos onde há
classificação de status HTTP.

## 3. Operacionalização (conservadora)

- Novo workflow `stj-tjro-sync.yml` com **`workflow_dispatch` apenas** (sem cron neste
  RFC): jobs `stj-acordaos` e `tjro-juris` chamando os CLIs com parâmetros de janela.
  Ligar cron é decisão do owner após rodadas manuais bem-sucedidas — basta acrescentar
  `schedule:` depois.
- Documentar no README de cada módulo (docstring do `__main__`) o comando de execução
  manual com `uv run`.

## 4. Critérios de aceitação

- `uv run pytest -q` verde com as novas suítes; nenhuma chamada de rede em teste.
- `tests/stj_acordaos/` e `tests/tjro_juris/` existem com cobertura dos módulos acima.
- Workflow dispatch-only validado por `actionlint`/inspeção (não executado em CI de PR).

## 5. Riscos

Fixtures desatualizadas em relação à API/HTML reais → manter fixtures mínimas e datadas;
a validação contra o mundo real continua sendo a execução manual do dispatch.
