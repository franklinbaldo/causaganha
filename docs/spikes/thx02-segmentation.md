# Spike — THX-02 como classificador de regiões de decisões judiciais

Status: experimental, sem inferência real medida no sandbox, **não integrado à produção**.
Relaciona-se ao spike de outcome #1687 e à avaliação de regiões #1055. O baseline formal continua sendo OPF #1053.

## Tese

A API `THX-02` não produz spans com offsets: retorna escolhas entre alternativas fixas e respectivas probabilidades. A versão inicial propõe:

1. Divisão **determinística** em unidades de até 600 caracteres, priorizando parágrafos, cabeçalhos de seções e fronteiras de sentenças. Mantém o intervalo `[start, end)` do original, sem reescrever texto.
2. Para cada unidade, enviar `trecho` mais contexto anterior/posterior (até 200 caracteres de cada lado) como `state`. Perguntar por um `choice` de papel estrutural (`cabecalho`, `ementa`, `relatorio`, `fundamentacao`, `preliminar`, `voto`, `dispositivo`, `custas`, `honorarios`, `encerramento`, `outro`).
3. Aceitar somente o papel selecionado com probabilidade >= 0,80 (valor **não calibrado no CausaGanha**). `outro`, respostas malformadas ou baixas probabilidades geram abstenção.
4. Reunir unidades adjacentes aceitas com o mesmo papel. Abstenções interrompem continuidade. As fronteiras são aproximadas pelas unidades; **não** são offsets extraídos pelo modelo.

Classificar *regiões* não substitui automaticamente os 26 rótulos de âncora v7. Em particular, `resultado`, `valor_condenacao`, `ref_processual` e `fundamentacao_legal` ainda exigem extração pontual. `dispositivo` também pode conter honorários/custas e outras cláusulas, não necessariamente uma única categoria: erros por fronteira grossa são um dos alvos do experimento.

## Contrato HTTP verificado

[Referência oficial](https://api.hal-x.ai/docs/thx-02/), 06/11/2026:

- `POST https://api.hal-x.ai/v1/decide/batch`
- Envelope `{"model":"thx-02","items":[{"state":{"trecho":"...","anterior":"...","posterior":"..."},"questions":{"papel":{"type":"choice","instructions":"...","criteria":{...}}},"think":false,"tta":1}]}`.
- Resposta `{"results":[{"answers":{"papel":{"type":"choice","choice":"...","probabilities":{"...":0.95}}}}]}`. Sem suposição de offsets no retorno.
- Até 1.024 estados por lote, 64 perguntas por estado. Cota anônima de **60 decisões por minuto/IP**, contando cada pergunta como decisão (não basta fazer um único lote). O spike limita o documento a no máximo 60 unidades no modo gratuito; default ainda menor, 40.
- Sem `HALX_API_KEY`, o endpoint aceita tráfego anônimo limitado. Não envie material sigiloso à API externa.

## Reproduzir

```bash
python -m pytest -q tests/test_spike_thx02_segmenter.py
python scripts/spike_thx02_segmenter.py
python scripts/spike_thx02_segmenter.py --audit-train data/segmenter_splits/train.jsonl
# Somente texto inteiramente fictício, egress explicitamente habilitado:
python scripts/spike_thx02_segmenter.py --live --source tests/fixtures/thx02_segmenter_synthetic.jsonl
```

`--audit-train` realiza **somente** a auditoria da discretização contra os limites do treino, sem chamadas à HAL-X. Calcula, entre as âncoras estruturais do gold que têm início/fim, quantas estão a até 60 caracteres de uma borda de unidade. É teto potencial **de pré-processamento**, não recall/F1 do THX-02. A amostra v7 tem 14 exemplos de treino, 3 de validação e 3 de teste; a avaliação final travada nunca deve ser aberta neste spike. Preferir, para o passo seguinte, releases v8 com revisão independente e splits imutáveis.

## Resultados obtidos no sandbox

- 19 testes locais passaram: offsets, segurança de modo offline, resposta de lote, abstention, cota, contrato e fechamento de regiões.
- Exemplo sintético: 1 documento com **5 unidades**, sem envio HTTP no modo padrão.
- Serviço real indisponível neste sandbox por falha de DNS. **Zero inferências reais**, nenhuma estimativa de F1, latência ou calibração.

## Próximos experimentos / critério de decisão

1. Primeiro, auditoria offline das bordas do `train.jsonl` e dos datasets v8 adjudicados (sem consultar o holdout). Se teto de fronteiras for inadequado, melhorar a granularidade ou testar detecção de âncoras, em vez de gastar chamadas.
2. Smoke remoto apenas no sintético; registrar status, request id, tempo de rede, probabilidades e erros, respeitando rate limit.
3. Ajustar regras e threshold exclusivamente no split de desenvolvimento, e estimar por tribunal/tipo de documento F1 de região, IoU de regiões, cobertura/abstenção, desvio médio de limites e custo/1000 decisões. Nunca confundir `confidence` do provedor com probabilidade da alternativa vencedora.
4. Confrontar **mesmo corpus e mesmo gold** com OPF #1053, como exige #1055. O THX-02 pode servir como *teacher* para propor rótulos, nunca como oráculo de sua própria avaliação. Sem adjudicação independente, pseudo-label não é gold.
5. Antes de trocar a arquitetura, medir se o ganho compensa o custo por unidade e os erros de granularidade, especialmente decisões OCR em linha única, referências jurídicas abreviadas e regiões mistas.

## Sobre “melhorar os pesos”

Mudar `criteria`, os contextos e o limiar via API **não atualiza pesos do THX-02**. Um fluxo factível: usar THX como anotador/propositor inicial, selecionar casos de maior incerteza, adjudicar (pessoa ou painel independente) e refinar o segmento OPF com dados reais numa versão de checkpoint nova, rastreável, respeitando treino/validação/holdout. Fine-tuning do próprio THX-02 exigiria uma receita de treino compatível com seus pesos locais e infraestrutura GPU; não faz parte deste spike nem está demonstrado apenas por existir checkpoint público.

**Regra de promoção:** nenhum resultado do spike altera classificação, scoring ou dados de produção sem benchmark validado.