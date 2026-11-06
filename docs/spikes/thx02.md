# Spike — THX-02 para classificar resultados judiciais

**Status:** experimental; somente leitura; não integrado ao pipeline de produção.
**Contrato verificado em:** https://api.hal-x.ai/docs/thx-02/ (2026-11-06).

## Hipótese

O modelo THX-02 da HAL-X pode classificar o **resultado operativo** de decisões brasileiras por perguntas de alternativas fechadas, com probabilidades, talvez reduzindo o custo de fallbacks generativos e erros de heurísticas em acórdãos. **Nenhuma superioridade ou calibração jurídica foi demonstrada ainda.**

## Escopo entregue

- `scripts/spike_thx02.py`: cliente batch HTTP (`POST /v1/decide/batch`) somente sob `--live`, sem chave para o free tier ou usando `HALX_API_KEY` do ambiente. Modelo explícito `thx-02`, 4 perguntas em uma requisição por documento, com `think` opcional e `tta=1|4`.
- `tests/fixtures/thx02_spike.jsonl`: 12 atos **inteiramente fictícios** com resultados conhecidos e casos de inversão da polaridade recursal; nenhum texto pessoal é enviado por padrão.
- `tests/test_spike_thx02.py`: testes offline do contrato, probabilidades, erro de modelo, inversão recursal, abstenção, métricas e consentimento para transferência externa.
- `.github/workflows/thx02-spike.yml`: smoke **não bloqueante** em PR com textos sintéticos, para observar a inferência real em ambiente com rede. Nunca usa dados identificáveis; publica resultados como artefato de diagnóstico.

## Contrato API (THX-02)

- `POST https://api.hal-x.ai/v1/decide/batch` com `{"model":"thx-02","items":[...]}`.
- Cada item: `state` (texto), `questions` (mapa de objetos `{type:"choice", instructions, criteria}`), `think`, `tta`.
- Batch retorna `results` alinhados à ordem dos documentos; cada resposta tem `model`, `answers`, `usage`, `latency_ms`.
- Para `choice`, usar `answers[name].probabilities[answers[name].choice]`, **não** o campo `confidence`, pois este mede distância de um palpite uniforme.
- Sem chave: até **60 decisões por minuto/IP** (cada pergunta conta). Este experimento limita cada execução a 12 documentos × 4 perguntas = 48 decisões. O servidor pode aplicar outras restrições e erro 429; não há retentativa automática no spike.
- Não oferece `cite` ou `excerpt` no THX-02; a evidência textual/proveniência deve continuar independente. Não se pressupõe que as probabilidades sejam calibradas para o domínio jurídico.

## Execução

```bash
# Formato/fixture/offline. Não envia nenhum documento nem precisa de dependências adicionais.
python scripts/spike_thx02.py

# Smoke real com 12 textos fictícios (usa cota gratuita da API).
python scripts/spike_thx02.py --live --output /tmp/thx02-sintetico.jsonl

# Opções de ablação: think:auto + quatro ordens de alternativas.
python scripts/spike_thx02.py --live --think --tta 4 --limit 3 \
  --output /tmp/thx02-tta.jsonl

# O benchmark contém textos públicos, mas pode conter dados pessoais.
# Só executar se houver autorização para transferência a terceiro.
python scripts/spike_thx02.py --gold-dir data/benchmark/decisions --limit 12 \
  --live --permit-third-party --output /tmp/thx02-gold.jsonl

# JSONL alternativo: uma linha por {"id":"...", "text":"...", "gold_outcome":"...", "gold_winner":"A|P|draw|unknown"}
python scripts/spike_thx02.py --input /tmp/decisoes-revisadas.jsonl --live \
  --permit-third-party --output /tmp/thx02-avaliacao.jsonl

# Regressão puramente offline
python -m pytest tests/test_spike_thx02.py -q
```

Os resultados gerados preservam `id`, classificações, probabilidade selecionada, uso e latência reportada pelo servidor, mas **não reproduzem o texto**. O caminho de saída deve ficar fora do Git. Nenhum texto é transmitido a HAL-X sem `--live`. Para fontes de terceiros, também é necessário `--permit-third-party`.

## Taxonomia e cuidados semânticos

O experimento pergunta por (1) tipo de ato, (2) `outcome` do **dispositivo atual**, (3) polo do recorrente e (4) vencedor direto como **diagnóstico independente**. O vencedor produzido pelo caminho proposto **não** usa a resposta direta: é calculado por um resolvedor conservador a partir de resultado e polo do recorrente, aplicando threshold sobre a probabilidade selecionada.

- Primeira instância: `procedente → A`, `improcedente → P`, `acordo → draw`.
- Recursos: `provido + A → A`, `provido + P → P`, `não provido + A → P`, `não provido + P → A`.
- **Abster** (`unknown`): resultado parcial, não conhecimento, prejudicialidade, extinção sem mérito, despacho/interlocutória sem resolução final, polo recorrente desconhecido/múltiplo e classificação abaixo do threshold.
- **Atenção:** o mapeamento acima é um proxy limitado para casos simples. Em ações com múltiplos pedidos, múltiplos recursos, provimento apenas formal e controvérsia cujo mérito já foi decidido antes, o polo vencedor substantivo não pode ser inferido da palavra “provido”. O sistema de produção precisa de resolvedor com contexto de instância, pedido e dispositivo precedente. `winner_direct` é apenas uma segunda estimativa a auditar.

Esta abstenção intencional impede que o spike invente vencedor em hipóteses juridicamente ambíguas, mas também limita a cobertura. O benchmark do repositório já documenta o alvo invariante em `data/benchmark/DESIGN.md`; no snapshot inspecionado, os nomes `recurso_resolver` e `benchmark_metrics` citados ali ainda não correspondem a módulos presentes na árvore `src/causaganha/analysis/`. Por isso o spike **não finge importar** esses módulos.

## Medidas produzidas e medidas pendentes

No modo `--live`, o resumo separa:

- Resultado superficial (`outcome_accuracy`): diagnóstico, não métrica principal.
- **Gate de ratabilidade**: precisão, recall e F1 para `winner != unknown`.
- **Condicional**: acerto do polo vencedor somente entre casos ratáveis no gold.
- Cobertura após abstenção; acerto do vencedor direto, apenas para contrastar com a regra.

Limitações: os 12 textos fictícios são **smoke tests**, não demonstram generalização. O gold antigo usa rótulos de LLM e alguns documentos não têm `recorrente_polo`; nesses casos a verdade para recurso vira `unknown`, não um rótulo inventado. Não usar essa amostra como prova de F1 real. Não foi implementada comparação ponta a ponta com `KeywordClassifier`, RAG ou Gemini, nem cálculo de intervalo de confiança. `latency_ms` é o tempo do modelo reportado pelo fornecedor, não o RTT; não representa latência de integração.

## Critérios de decisão após o spike

1. Smoke API: zero erro de contrato; modelo retornado THX-02; respostas com 4 distribuições válidas; resultados consistentemente ordenados.
2. Benchmark de pelo menos **200–500 decisões públicas revisadas**, estratificadas por fase, tipo e resultado. Garantir participação suficiente de recursos dos polos A e P, e revisão independente das situações parciais.
3. Comparar **mesmo conjunto** no THX-02, `KeywordClassifier`, RAG e LLM; reportar macro-F1 por polo, F1 do gate, cobertura por threshold, erro de alta confiança, Brier/ECE, latência de rede e custo por decisão.
4. Somente propor integração na produção se houver melhoria estatística e proteção adequada a dados pessoais. Um mecanismo de rollback e a preservação de evidência/proveniência são pré-requisitos.

## Resultado desta execução

- Testes unitários do spike: **29/29 aprovados** localmente com Python 3.13.
- Dry-run: 12 itens, 4 perguntas por item, 48 decisões potenciais; sem transmissão externa.
- Chamada ao endpoint real: **não executada localmente** porque o sandbox não resolve DNS externo; o workflow de PR tentará somente o conjunto sintético sem colocar essa disponibilidade como condição para integrar o spike.

**Leitura:** viabilidade de contrato e implementação demonstradas offline; eficácia jurídica real ainda não medida.
