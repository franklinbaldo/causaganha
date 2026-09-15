---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2hb3sq-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-f0q3d4/ (rodada mais recente concluída, 21:26-21:49Z), knowledge/backlog/issue-1051.md"
finding: "Tensão AgentRun-vs-Wisk documentada e resolvida por precedente (decision-follow-scheduled-scaffold-again, repetida em >=4 rodadas): seguir o scaffold explícito do prompt agendado, sem nova notificação enquanto nada mudar. next_move de f0q3d4 aponta #1051 como única frente de domínio desbloqueada e não esgotada, com pool de candidatos pareáveis (annotator_config.seeded_with=='none' na anotação existente) e um padrão de erro de âncora longa a considerar. Corrigi e ampliei essa leitura: recomputando o pool com a checagem correta de independência (mechanical.annotations_are_independent sobre TODAS as combinações de anotações existentes, não só contar unseeded==1), encontrei 18 candidatos reais, incluindo os 2 documentos que f0q3d4 tinha marcado como 'órfãos e não recuperáveis' (doc_b8a4a405.../doc_ec1f5133...) -- na verdade são recuperáveis: bastava uma TERCEIRA anotação de família distinta da já existente (unseeded), não uma segunda para o par seeded histórico."
---

# Leitura: conhecimento OKF relevante

1. **`knowledge/agent-runs/index.md`** e **`.claude/hourly-loop.md`**: o
   loop horário oficial do CausaGanha migrou para o runtime Wisk
   (`uv run wisk start`); `AgentRun`/`AgentReading`/... em
   `knowledge/agent-runs/` são declarados legado, sem novas instâncias
   esperadas. O prompt agendado que dispara esta sessão, porém, continua
   instruindo explicitamente o scaffold legado sem ressalva. Pelo menos 4
   rodadas consecutivas (to0ars, bueov4 em 14/09; 50ns70, yz281l, f0q3d4 em
   15/09) já identificaram essa tensão; duas notificaram o usuário
   proativamente sem resposta/mudança de estado desde então. Sigo o mesmo
   precedente: obedecer ao prompt agendado, não repetir notificação sem
   fato novo (nenhuma PR/handoff Wisk em voo nesta janela, `uv run wisk
   start` reportado por f0q3d4 como blocked/no-eligible-session).

2. **Rodada f0q3d4 (mais recente concluída, 21:26-21:49Z)**: escalou
   ReviewRecords de #1051 de 27 para 29 (PR #1531, mesclada). `next_move`
   registrou (a) pool real caído de 13 para 11 candidatos elegíveis, meta
   textual 30-50 documentos, piso RFC 0012 §5.4 (>=30) a 1 incremento de
   distância; (b) dois documentos (`doc_b8a4a405...`, `doc_ec1f5133...`)
   marcados como órfãos -- anotação extra gravada mas sem review, por não
   formarem par independente com a anotação histórica **seeded** já
   existente desses dois documentos; (c) padrão de âncora longa demais em
   `acordao_decisorio_inicio`/`resultado` observado 2/2 vezes nos
   subagentes daquela rodada, a considerar reforçando o prompt canônico.

3. **Correção desta rodada sobre o ponto (b)**: reli
   `src/segmenter_dataset/mechanical.annotations_are_independent` e
   `store.py::_require_independent_inputs` -- independência é uma
   propriedade de **par**, não do documento como um todo. Um documento com
   uma anotação seeded histórica + uma anotação unseeded (já gravada por
   f0q3d4) ainda pode virar par independente se eu adicionar uma
   **terceira** anotação unseeded de família distinta da já gravada
   (ignorando a seeded). Recomputei o pool checando
   `combinations(anotações_do_doc, 2)` para nenhum par já independente, e
   `>=1 unseeded` como sinal de recuperabilidade -- 18 candidatos reais
   (não 11), incluindo os 2 "órfãos" de f0q3d4. Escolhi justamente esses 2
   como alvo desta rodada: aproveita trabalho de anotação já feito e
   parado, em vez de deixá-lo parado indefinidamente.

4. **`knowledge/backlog/issue-1051.md`**: ainda registra `status: blocked`
   com `last_verified_at: 2026-09-07`, antes do mecanismo de subagente
   isolado como substituto do "human annotator" ter começado a produzir
   incrementos reais (9+ rodadas desde então). Registro aqui como
   inconsistência entre código/knowledge a corrigir numa rodada futura;
   não a esgotei nesta para não desviar do incremento de domínio.
