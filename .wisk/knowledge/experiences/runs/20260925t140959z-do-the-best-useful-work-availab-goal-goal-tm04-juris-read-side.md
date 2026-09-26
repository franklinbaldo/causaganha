---
type: "RunGoal"
id: "run-goals/20260925t140959z-do-the-best-useful-work-availab/goal-tm04-juris-read-side"
run: "runs/20260925T140959Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Fechar o lado de leitura do gap TM-04 (docs/SECURITY_THREAT_MODEL.md, issue #1610) para juris: validar o rodape KV_METADATA (causaganha.schema_version/causaganha.item_id) de cada arquivo_ia_url de fonte juris antes de causaganha.processos.service.buscar_processo compor read_parquet, e espelhar a mesma checagem no lado Web (web/src/lib/processoCnj.ts)."
rationale: "O lado de escrita (tjro_juris.service._rows_to_parquet gravando o rodape) ja fechou numa rodada anterior (PR #1648, mesclada). O lado de leitura para djen ja existe (service._validar_metadata_djen/_validar_metadata_djen_urls, e o espelho TS validarMetadataDjen/validarMetadataDjenUrls) mas juris nunca ganhou o equivalente -- buscar_processo compunha read_parquet(juris_urls) sem nunca ler o rodape que o proprio artefato agora declara sobre si, deixando um artefato juris trocado sob uma URL inalterada indetectavel exatamente como o lado djen ja protege contra."
success_signal: "Testes novos provam RED->GREEN nos dois runtimes: Python (TestMetadataJurisCoerente + 2 testes de integracao em tests/causaganha/processos/test_service.py) e TypeScript (describe blocks espelhados em web/src/lib/processoCnj.test.ts) passam; suite completa de cada lado permanece verde; ruff check/format --check e npm run typecheck limpos; docs/SECURITY_THREAT_MODEL.md TM-04 atualizado para registrar o lado de leitura fechado para juris, com o gap restante (stj/datajud sem pipeline de export) explicitamente delimitado."
status: "achieved"
---

# RunGoal
