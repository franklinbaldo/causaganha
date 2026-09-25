---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-r0zxiq-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 21 abertas)"
finding: "#1610 (security(archive): validar URLs de manifestos e invariantes de proveniência antes do DuckDB) é a única issue de segurança aberta, e a única com um checklist de conclusão explícito no corpo. Lida a issue inteira: 4 critérios de conclusão -- (1) validador central de URL/artefato: feito (`_validate_artifact_url`/`validateArtifactUrl`); (2) nenhum `read_parquet` recebe URL sem validação: feito para djen/juris (mesclado antes desta rodada, PRs #1646/#1648/#1650) e agora para datajud (esta rodada); stj usa item fixo, sem checagem de tribunal aplicável (documentado); (3) invariantes de identidade/proveniência antes da composição: feito para djen/juris/datajud (write+read, Python+TS); stj permanece fora de alcance porque `stj_acordaos` não tem nenhum pipeline `write_parquet`/`to_parquet` sob controle deste repo -- decisão já registrada por rodada anterior, reconfirmada por esta; (4) regressões de egress/atribuição cobertas por teste: feito nos dois lados. Verificado em `src/datajud/archive.py` (grep por `write_parquet`) que datajud, diferente de stj, TEM um pipeline de export Parquet sob controle deste repo (`_write_parquet`, usado por `datajud.service.persist`) -- a frase de `docs/SECURITY_THREAT_MODEL.md` TM-04 que agrupava 'stj/datajud continuam sem emitir esse rodapé... porque stj_acordaos não tem pipeline' estava factualmente incorreta para datajud (a razão dada só vale para stj); confirmado também que `causaganha/processos/service.py::buscar_processo` já chamava `_validar_metadata_djen_urls`/`_validar_metadata_juris_urls` mas passava `datajud_urls` direto para `_build_datajud` sem checagem de rodapé equivalente, e o mesmo gap existia no espelho TS (`web/src/lib/processoCnj.ts`, linha ~1220 chamava só `fonteUrls` para datajud, sem `validarMetadataDatajudUrls`). Esse gap concreto, delimitado e simétrico nos dois runtimes foi selecionado como trabalho desta rodada -- continuação direta do next_move item (1) do relatório mais recente (qjwekj), que já apontava o lado de leitura de juris como próximo passo; essa parte já foi fechada por uma sessão paralela (PR #1650, sistema 'Wisk', ver reading-okf) antes desta rodada iniciar, então o avanço real restante e ainda não fechado por ninguém era datajud, não juris. Demais 20 issues abertas seguem sem fato novo: Parquet/CNJ (#1470/#1469/#1471/#1472/#1468/#1022/#985) bloqueadas por credenciais IA ausentes (10+ rodadas, ver knowledge/backlog/); segmenter (#1050 e derivadas) com PR #1605 ainda bloqueada por conflito de merge em branch alheia sem permissão de push desta sessão; #951/#1093 produto de longo prazo sem gate de rodada única."
---

# Leitura: issues abertas

21 issues abertas revisadas via `list_issues`, cruzadas com o corpo
completo de `#1610` (checklist de conclusão) e com `docs/SECURITY_THREAT_MODEL.md`
TM-04. `#1610` é a única issue de segurança aberta; seu gap restante e
realmente acionável nesta janela é `datajud` (que tem pipeline de export
Parquet sob controle deste repo, ao contrário de `stj`) -- o texto do
threat model que dizia o contrário estava incorreto. Selecionado como
trabalho desta rodada. As demais 20 issues são trilhas de longo prazo sem
fato novo desde as rodadas anteriores.
