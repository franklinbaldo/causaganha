---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-2cjjig-decision-ementa-extends-to-eod-consistency"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
goal_id: "2026-09-15-exciting-mccarthy-2cjjig-goal-scale-segmenter-reviews"
question: "Os dois documentos desta rodada (doc_613907cc, doc_69b98539) sao exports de capa+ementa-estruturada do TJRO (EMENTA + I. CASO EM EXAME / II. QUESTAO EM DISCUSSAO / III. RAZOES DE DECIDIR / IV. DISPOSITIVO E TESE), sem secao de relatorio ou voto separada. Os dois subagentes Tecnica 1 independentes, cada um vendo so o seu documento, discordaram entre si sobre onde a regiao ementa termina: no doc1 o subagente fechou como nao-casado (estende ate EOD, tratando as 4 secoes numeradas como parte da ementa publicada); no doc2 o mesmo subagente-tipo fechou cedo, logo apos o paragrafo-topico e antes de 'I. CASO EM EXAME', tratando as 4 secoes como fora da ementa. Qual leitura adotar na adjudicacao, e deve ser a mesma para os dois documentos do mesmo formato?"
choice: "Adotada a leitura 'estende ate EOD' (nao-casado) para AMBOS os documentos -- doc1 mantido como o subagente enviou; doc2 teve o fim precoce de B removido na resolucao, revertendo para nao-casado. Motivo: a 'ementa estruturada' (CASO EM EXAME/QUESTAO EM DISCUSSAO/RAZOES DE DECIDIR/DISPOSITIVO E TESE) e o formato de ementa que o TJRO efetivamente publica nestes exports de capa -- nao ha relatorio nem voto separados em nenhum dos dois documentos, entao as 4 secoes numeradas SAO o conteudo publicado como ementa, nao uma secao posterior e distinta dela."
rationale: "A guideline (annotation_guideline_v7.md) define ementa_fim como 'Last line before RELATORIO' -- um cue de fechamento real, nao qualquer ultimo texto do documento. Nenhum dos dois documentos tem relatorio real, entao esse cue nunca existe aqui por definicao estrutural do formato de export, nao por uma falha pontual de um documento especifico. Fechar ementa logo apos o paragrafo-topico (como B fez em doc2) exigiria um cue de fechamento genuino que simplesmente nao existe no texto -- o anti-pattern da propria guideline e 'fabricar' uma tag de fechamento por conveniencia. Tratar os dois documentos do mesmo formato de forma diferente (um nao-casado, outro casado num ponto arbitrario) introduziria ruido de rotulagem sem justificativa textual -- a mesma classe estrutural de documento deve ter a mesma leitura de fronteira, e essa leitura e a mais fiel ao que a guideline pede (fechar apenas com um cue real)."
---

# Decisão: fronteira de `ementa_fim` em exports de capa+ementa-estruturada do TJRO

Dois subagentes Técnica 1 genuinamente independentes (um por documento,
nenhum viu o outro) discordaram entre si sobre a mesma questão estrutural
em dois documentos do mesmo formato. Resolvida na adjudicação com a leitura
"estende até EOD" para os dois, por ser a mais fiel à guideline (que exige
um cue de fechamento real, ausente em ambos os casos) e por evitar tratar
de forma inconsistente dois documentos da mesma classe estrutural.
