---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-b3xdwp-evidence-review-doc-dd458d79"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_dd458d79ebdf7c65daf39d1a51cf1ea9/rev_a408ee540d1e30dc4dcf828dce56abc5.xml"
summary: "15º ReviewRecord real da store (review_count 14->15), atingindo o success_signal do goal desta rodada (>=15). Subagente Técnica 1 isolado (general-purpose, segunda tentativa nesta rodada -- a primeira retornou zero tags e foi descartada sem ingestão, ver evidence-doc-dd458d79-zero-tag-attempt) produziu ann_3c3158f122f62d28a7f0e9e3239ac5a0 (model_family=prompt_subagents:general-purpose, seeded_with=none -- par independente confirmado True com a anotação histórica ann_41de99d49a20b4176f1c56f9672c2d4f, model_family=prompt_subagents:haiku, seeded_with=none). Verbatim-fidelity verificada programaticamente antes da ingestão. Diff exato: 1 span concordante (resultado), 6 só no subagente (cabecalho_inicio/fim, capitulo_merito_inicio/fim, ref_processual, fundamentacao_legal -- falso negativo total do histórico), 1 só no histórico (ementa_fim). Resolução adotou integralmente a anotação do subagente: os 6 spans exclusivos foram aceitos como achados reais (mesmo padrão de falso-negativo total em exports capa+ementa-estruturada já identificado em 2cjjig); ementa_inicio resolvido a favor do cue literal 'Ementa:' (rejeitando o ancoramento do histórico no primeiro conteúdo substantivo); ementa_fim manteve-se não-casado (estende até EOD), rejeitando o fechamento fabricado do histórico dentro da seção 'Jurisprudência relevante citada' -- terceira ocorrência do mesmo disagreement estrutural do dia, ver decision-ementa-precedent-reapplied-doc-dd458d79 e decision-codify-ementa-eod-in-guideline (guideline atualizada para v7.4 nesta rodada para evitar uma quarta re-adjudicação)."
---

# Review real #15: doc_dd458d79ebdf7c65daf39d1a51cf1ea9

`uv run python scripts/segmenter_governance_status.py` antes desta review: review_count=14. Depois: review_count=15 (meta do goal desta rodada, >=15, atingida).
