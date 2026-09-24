---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-e3tk18-reading-okf"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-24-exciting-mccarthy-i23hxr/run.md e knowledge/agent-runs/2026-09-24-exciting-mccarthy-{khpkk2,my6ovw,eb5f9r}/run.md; .claude/hourly-loop.md; knowledge/backlog/issue-1050.md; scripts/segmenter_semantic_audit.py; tests/segmenter_dataset/test_segmenter_audit_scripts.py; src/segmenter_dataset/store.py"
finding: "A rodada mais recente ja mesclada (i23hxr, PR #1606) fechou o ponto cego de teste para os tipos long_anchor/dispositivo_inside_voto e reparou os 4 achados reais que ele escondia, mas deixou explicito em seu next_move (ponto 4) que os demais tipos que scripts/segmenter_semantic_audit.py sabe detectar -- operative_on_reasoning_or_verb, capitulo_merito_on_prose, ref_processual_mismatch, ref_normativa_overlap -- 'nunca foram auditados manualmente contra o corpus real e podem esconder defeitos similares'. Confirmado ao vivo: rodar find_anti_patterns() contra data/segmenter mostra 0 achados desses 4 tipos (so os 7 fundamentacao_legal_collapsed/valor_condenacao_collapsed ja conhecidos aparecem). Construir fixtures sinteticas controladas (nao apenas rodar contra o corpus real) para cada um dos 4 tipos revelou que 3 funcionam corretamente (operative_on_reasoning_or_verb, capitulo_merito_on_prose, ref_processual_mismatch), mas ref_normativa_overlap e codigo morto: src/segmenter_dataset/store.py's _labels_to_text_element/_render_item sempre serializa cada label com um atributo ord=\"N\" (ex. <ref_normativa ord=\"1\">), mas scripts/segmenter_semantic_audit.py verificava a tag sem atributo por substring exata (\"<ref_normativa>\" in xml_text) e um regex sem atributo correspondente -- essa substring literal nunca ocorre em nenhum arquivo real, entao a checagem jamais dispara, independente de existir sobreposicao genuina no corpus. Confirmado programaticamente contra todo data/segmenter/annotations/: grep por '<ref_normativa>' e '<fundamentacao_legal>' (sem atributos) retorna 0 arquivos, enquanto a forma com ord=\"N\" e universal. .claude/hourly-loop.md reconfirmado sem mudanca: AgentRun e legado historico, novas rodadas do loop horario devem usar exclusivamente o Wisk, mas o prompt agendado desta sessao especifica continua instruindo a criacao de um AgentRun via .claude/agent-run-scaffold.md -- mesma tensao ja registrada por 7+ rodadas anteriores, sem fato novo que justifique reescalar de novo."
---

# Leitura: conhecimento OKF relevante

Releu o `run.md` da rodada imediatamente anterior nesta mesma janela
(`i23hxr`, ja mesclada como `#1606`) e o backlog de `#1050` para
entender continuidade antes de escolher o trabalho desta rodada.
`i23hxr` fechou o ponto cego de teste para dois dos seis tipos de
finding sem cobertura (`long_anchor`, `dispositivo_inside_voto`) e
deixou os outros quatro (`operative_on_reasoning_or_verb`,
`capitulo_merito_on_prose`, `ref_processual_mismatch`,
`ref_normativa_overlap`) explicitamente como o proximo passo natural
em seu `next_move`.

O achado que efetivamente moveu esta rodada veio de tentar fechar
essa lacuna com fixtures sinteticas controladas, nao so relendo
relatorios ou rodando o script contra o corpus real: `ref_normativa_overlap`
e estruturalmente codigo morto desde que foi escrito, porque compara
contra uma forma de tag (`<ref_normativa>` sem atributos) que o
proprio serializador da store nunca produz (`<ref_normativa ord="N">`
com o atributo `ord` sempre presente). Nenhuma das rodadas anteriores
que ja rodaram este script (~27+ vezes) percebeu isso, porque todas
liam apenas a saida agregada contra o corpus real (que sempre mostra
zero achados desse tipo) sem nunca testar isoladamente se o proprio
detector funciona. Ver `goal_ids`/`decision_ids`/`evidence_ids` para o
processo TDD que corrigiu isso.

Releu tambem `.claude/hourly-loop.md`: sem mudanca desde a ultima
verificacao desta janela. A tensao AgentRun-vs-Wisk permanece
registrada, sem fato novo que justifique reescalar de novo.
