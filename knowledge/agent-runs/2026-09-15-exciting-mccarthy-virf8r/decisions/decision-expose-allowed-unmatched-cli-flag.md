---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-virf8r-decision-expose-allowed-unmatched-cli-flag"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
goal_id: "2026-09-15-exciting-mccarthy-virf8r-goal-scale-segmenter-reviews"
question: "scripts/adjudicate_segmenter_review.py::build_review já aceita allowed_unmatched, mas a CLI (main) não o expunha -- ao adjudicar um acórdão em modelo por tópicos sem cue de fechamento de ementa (doc_0bb1cdf4d3ce8cb2400765e788c767e4), não havia forma de declarar essa razão via CLI, só chamando build_review diretamente em Python. Corrigir a CLI (mudança pequena, mirrorando scripts/annotate_second_independent.py) ou contornar chamando build_review manualmente para este documento?"
choice: "Corrigir a CLI, adicionando --allowed-unmatched (JSON base -> razão), com TDD (RED confirmando SystemExit por 'unrecognized arguments', GREEN depois)."
rationale: "Um caso legítimo de unmatched (RFC 0012/guideline já preveem isso explicitamente) é exatamente o tipo de disagreement que a adjudicação deve conseguir registrar pela mesma ferramenta usada em todo o resto do processo -- contornar via chamada Python direta quebraria a reprodutibilidade via linha de comando que o resto do mecanismo (annotate_second_independent.py já tem o mesmo flag) estabelece como padrão. A mudança é pequena, sem risco de regressão (novo argumento opcional com default '{}'), e generaliza a ferramenta para qualquer rodada futura que encontre o mesmo caso, em vez de resolver só para este documento."
---

# Decisão: expor --allowed-unmatched na CLI de adjudicação

Escolhi a correção estrutural (CLI) em vez do atalho pontual (chamar build_review em Python só para este documento), porque o gap era da ferramenta, não do caso -- e a ferramenta é reutilizada pelas próximas rodadas.
