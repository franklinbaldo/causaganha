---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal: "Fechar o gap de #1610 em ManifestJuris.load_text: rejeitar mes_ano que não tenha a forma canônica YYYY-MM, antes que _juris_url (causaganha.decisoes.published) o interpole numa URL consumida por read_parquet([...]) em causaganha.decisoes.search."
rationale: "O manifesto JURIS é buscado ao vivo de archive.org (juris_archive.read_manifest_text) toda vez que decisoes_buscar roda com fonte='juris'/'todas' — é exatamente a classe de artefato canônico que #1610 pede para proteger ('manifest/index envenenado controla URL entregue a DuckDB'). ManifestJuris.load_text nunca validou a forma de mes_ano; como urllib.parse.quote() preserva '/' por padrão (safe='/'), um mes_ano malicioso sobrevive intacto até a URL final. Esse caminho de código não foi coberto por nenhuma auditoria anterior de #1610 (nem TM-03/TM-04, nem o handoff Wisk arquivado), que corretamente descartou o caminho vizinho resolve_juris_urls_for_cnj como não-vulnerável mas nunca examinou este."
success_signal: "Reprodução ao vivo (antes da mudança) mostra discover_published_juris_datasets(manifesto_malicioso) produzindo uma URL com '../../' sobrevivente; testes novos em tests/tjro_juris/test_juris_manifest.py (8 casos parametrizados + 1 caso válido) e tests/causaganha/decisoes/test_published.py (1 caso) provam RED->GREEN: ManifestFormatError é levantado antes que qualquer URL maliciosa seja construída, casos válidos (YYYY-MM) continuam passando. ruff check/format --check limpos (incluindo TRY301). Suite completa (pytest -q) e okf-parser check permanecem verdes."
status: "achieved"
---

# Goal: validar `mes_ano` do manifesto JURIS antes de virar URL

Fecha um pedaço concreto e não auditado do critério de conclusão de
`#1610` ("nenhum `read_parquet` recebe URL de manifest sem validação"):
`tjro_juris.manifest.ManifestJuris.load_text` nunca validava a forma de
`mes_ano`, que é interpolado sem escaping adicional numa URL de
`read_parquet` em `causaganha.decisoes.search` toda vez que
`decisoes_buscar` consulta a fonte JURIS.
