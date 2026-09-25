---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-230b86-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-230b86"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. O trabalho desta rodada toca scripts/generate_catalog.py e tests/test_archive_partitions.py, fora das arquiteturas centrais nomeadas pelo guia (djen-backup/manifest, fronteira CSS/Panda, contratos .qmd) -- aplicam-se as regras gerais de 'Style' (ruff estrito, sem except Exception cego -- nenhum bloco de excecao novo introduzido nesta mudanca) e 'TDD como fluxo padrao', seguidas: 2 testes novos escritos primeiro contra a API alvo (discover_catalog_items ainda inexistente em scripts.generate_catalog), confirmados RED (AttributeError), depois GREEN apos extrair a funcao e corrigir main(). uv run ruff check/format --check limpos nos arquivos tocados. Tambem mesclada nesta rodada a PR #1651 (datajud KV_METADATA, TM-04), que seguiu o mesmo padrao de tjro_juris.service._rows_to_parquet ja documentado em rodadas anteriores -- revisada, nao redigida por esta sessao."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada. O trabalho
principal desta rodada (extrair `discover_catalog_items()` em
`scripts/generate_catalog.py` para impedir que uma rebuild
`--verified-inventory` caia em busca global do IA) não toca nenhuma das
arquiteturas centrais nomeadas pelo guia, mas segue as regras gerais de
estilo Python (ruff estrito) e o fluxo TDD padrão (RED confirmado via
`AttributeError` antes da implementação, GREEN depois). A rodada também
mesclou a PR #1651 (datajud KV_METADATA, TM-04), escrita por uma sessão
anterior seguindo o mesmo padrão já documentado para `tjro_juris` — só
revisada e mesclada aqui, não redigida por esta sessão.
