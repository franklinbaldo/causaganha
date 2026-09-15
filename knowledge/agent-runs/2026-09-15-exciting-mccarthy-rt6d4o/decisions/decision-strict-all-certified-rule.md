---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-rt6d4o-decision-strict-all-certified-rule"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
goal_id: "2026-09-15-exciting-mccarthy-rt6d4o-goal-direct-equality-processo-cnj"
question: "Como decidir o modo de igualdade da consulta DJEN quando uma busca por CNJ pode atravessar múltiplos arquivos Parquet (um por tribunal/ano)? Por arquivo (misturar igualdade direta e regexp_replace numa única UNION) ou tudo-ou-nada para a busca inteira?"
choice: "Tudo-ou-nada: resolveDjenEqualityMode(urls, kvRows) só retorna 'direct' quando TODOS os arquivos da busca certificam ambos os marcadores do rodapé com o valor exato; um único arquivo sem certificação (legado, futuro, ou com falha na leitura do rodapé) faz a busca inteira cair para o caminho compatível (regexp_replace), nunca por arquivo individual. Também: falha na própria consulta de certificação degrada para o caminho compatível (nunca vira aviso de 'fonte indisponível' nem propaga)."
rationale: "É o texto literal do critério de aceite de #1469: 'usar igualdade direta somente se TODOS os arquivos DJEN da busca declararem a capacidade. Arquivos mistos/antigos ou leitores sem suporte mantêm o caminho compatível.' Uma alternativa por-arquivo (cada branch do UNION ALL escolhendo seu próprio operador) seria tecnicamente possível -- buildDjenSql já monta um único FROM read_parquet([...]) com union_by_name, não um UNION ALL por arquivo -- mas exigiria reescrever a query inteira para uma estrutura por-arquivo só para economizar uma fração dos casos (buscas que cruzam tribunal/ano são raras: cada arquivo é um tribunal-ano e a maioria dos CNJs aparece em um só). O ganho não compensa a complexidade extra nem o risco de um bug sutil (aplicar igualdade direta a uma linha de um arquivo legado dentro do mesmo resultado agregado). Optei pela regra estrita, que também é a mais fácil de auditar e testar (7 casos cobrem: certificado único, múltiplos certificados, sem rodapé, marcador parcial, valor inesperado, mistura, zero arquivos)."
---

# Decisão: regra tudo-ou-nada para igualdade direta

`resolveDjenEqualityMode` decide para a busca inteira, não por arquivo -- inclusive quando um dos arquivos falha a própria checagem de certificação (tratado como não-certificado, nunca como erro fatal). Isso corresponde exatamente ao texto do critério de aceite de #1469 e evita a complexidade de reescrever `buildDjenSql` para uma estrutura por-arquivo.
