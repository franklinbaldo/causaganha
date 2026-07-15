# RFC 0011 — Gerador sintético estrutural para o Decision Segmenter

- **Status:** Proposto
- **Data:** 2026-07-15 (revisado na mesma data após review)
- **Relacionado:** RFC 0001 (diagnóstico do fine-tuning v7), ADR 0010 (Rebuild
  Segmenter Pipeline v7), PR #792 (treino headless Colab/Kaggle + W&B),
  docs/GOVERNANCE.md (política de dados)
- **Escopo:** dados sintéticos como fonte de treino de primeira classe para o
  segmentador de decisões (OPF, âncoras BIOES) — arquitetura do gerador, hard
  negatives, identidades fictícias, proveniência, invariantes anti-vazamento,
  protocolo experimental e fases de implementação.

## 1. Resumo executivo

**Dados sintéticos são uma fonte de treino de primeira classe para este
segmentador — não um suplemento provisório enquanto o gold escala, nem um
recurso a ser tolerado com desconfiança.** O corpus sintético pode
legitimamente exceder o real em contagem de documentos (1:1, 5:1, 10:1 ou
mais, conforme os experimentos indicarem). Um modelo de produção pode ser
treinado majoritariamente em exemplos sintéticos, desde que avaliado
inteiramente em documentos reais.

A tarefa é excepcionalmente adequada a isso (§2): o modelo aprende **âncoras
curtas e fronteiras estruturais**, não raciocínio jurídico. Um gerador
determinístico produz exemplos frequentemente **mais informativos** que a
amostragem passiva da distribuição real — especialmente para classes
estruturalmente raras, condições de fronteira difíceis, negativos
adversariais e combinações ausentes do seed.

O papel dos dados reais não diminui — muda de natureza (§3): o gold real
**define e audita a ontologia, calibra o gerador e fornece a validação e o
teste**. Os gates G1–G5 continuam contando somente gold real; validação e
teste continuam exclusivamente reais; `voto_*`/`acordao_decisorio_*`
continuam exigindo suporte gold genuíno (ADR 0010). O que o sintético não
pode substituir é a **avaliação** real e a **calibração** contínua — não o
volume de treino.

Arquitetura (§4, preservada): geração em três camadas onde o programa — não
o LLM — controla estrutura, âncoras e offsets iniciais. Treino real-only
**não é o modelo preferido presumido**: é um baseline entre vários regimes
comparados empiricamente (§12), com seleção de configuração feita em
**validação real** e o **teste real travado** até a configuração congelar.

Armazenamento (§15-bis): o corpus persistido (fase 2/LLM em diante) grava
**em dois lugares, não um ou outro** — o Internet Archive como fonte de
verdade de longo prazo, e um Kaggle Dataset privado como cache operacional
derivado dele para os drivers de treino do PR #792. Toda decisão de design
listada neste RFC está fechada (§16): as que são escolha de engenharia têm
resposta definitiva; as que dependem de dado empírico têm um procedimento
de decisão e um ponto de partida concreto, não um "?" em aberto.

## 2. Por que esta tarefa tem valor esperado incomum para sintético

O segmentador não é solicitado a produzir raciocínio jurídico correto nem a
decidir casos. Ele aprende:

- âncoras estruturais curtas (cues de 1–5 palavras, como o guideline manda);
- fronteiras de seção de documento;
- fórmulas operativas controladas;
- a distinção entre âncoras positivas e hard negatives;
- padrões estruturais de sentença/acórdão;
- invariância a ruído de extração.

Para esse alvo, a geração determinística tem propriedades que a coleta
passiva não tem:

1. **Rótulos exatos por construção** — o renderer registra offsets no
   momento da inserção (§4.3); não há custo de anotação nem erro de offset
   na origem.
2. **Estruturas raras geradas deliberadamente** em vez de esperar ocorrência
   natural — `preliminar_*`, `custas_*`, `voto_*` etc. aparecem com a
   frequência que o treino precisar, não com a frequência que o DJEN der.
3. **Minimal pairs controlados** — a mesma frase de superfície colocada em
   contexto positivo e negativo (§5), o contraste mais informativo possível
   para o modelo.
4. **Combinações ausentes do seed** representadas (acórdão com preliminar +
   voto vencido + honorários, por exemplo — pode não existir nos 20 docs).
5. **Balanceamento de classe controlado**, impossível num corpus natural.
6. **Ruído de extração variado sistematicamente**, cobrindo o espaço de
   artefatos em vez de amostrá-lo.
7. **Pré-treino sintético** pode dar competência estrutural ampla antes do
   fine-tuning real (Run B, §12).

O RFC 0001 diagnosticou exatamente as lacunas que isso ataca: `preliminar_*`
só no test set, val cobrindo 17/25 categorias, 1–4 spans por classe rara no
corpus inteiro. Coletar e anotar gold real resolve isso lentamente; o
gerador resolve a *exposição de treino* imediatamente — e o gold real
continua resolvendo o que só ele pode (§3).

## 3. O papel dos dados reais genuínos

Real e sintético têm papéis distintos; nenhum torna o outro secundário:

- **Definir o que estrutura válida realmente é** — a ontologia nasce e é
  auditada contra documentos reais;
- **Descobrir variantes de superfície novas** — phrase banks crescem a
  partir do observado, não do imaginado;
- **Calibrar frequências e estilos** (§6.1) — o gerador é recalibrado
  conforme novo gold real é anotado;
- **Detectar pontos cegos do gerador** — erro em validação real que o
  sintético não cobre é sinal de recalibração;
- **Validar e testar generalização real** — exclusividade absoluta do real.

Compromissos mantidos sem exceção:

- G1–G5 contam **somente gold real pristino** — volume sintético não compra
  cobertura de corpus;
- validação e teste são **somente reais**;
- `voto_*` e `acordao_decisorio_*` exigem suporte gold genuíno (ADR 0010);
- anotação de gold real continua continuamente;
- o gerador é recalibrado a partir do gold novo.

## 4. Arquitetura do gerador (três camadas)

### 4.1 Camada 1 — plano abstrato (`DocumentSpec`)

```python
DocumentSpec(
    doc_type="acordao",
    tribunal_style="tjro_2grau",
    sections=[
        "cabecalho", "ementa", "relatorio", "preliminar",
        "voto", "honorarios", "acordao_decisorio", "encerramento",
    ],
    outcome="parcialmente_provido",
    has_monetary_award=True,
    has_costs=True,
    has_dissent=False,
    noise_profile="djen_pdf_extraction",
)
```

Controla: sentença vs. acórdão; presença e ordem de seções; decisão
monocrática vs. colegiada; preliminares; honorários/custas; valores;
variações tipográficas e ruído. Amostragem com seed explícito.

### 4.2 Camada 2 — conteúdo interno (sem poder sobre rótulos)

O conteúdo factual/argumentativo de cada seção é preenchido sem decidir
rótulos nem tocar offsets — phrase banks gramaticais na fase 1, LLM na
fase 2 (§14), trechos reais em registros híbridos (§6.2). Requisitos:
identidades fictícias por padrão (§7), números processuais sintéticos,
valores amostrados, áreas jurídicas e estilos variados.

### 4.3 Camada 3 — renderer determinístico

O programa escolhe e posiciona as âncoras, registrando cada offset no
momento da inserção:

```python
start = len(buffer)
buffer.append("Ante o exposto")
end = len(buffer)
labels.append({"category": "dispositivo_abertura", "start": start, "end": end})
```

**Garantia precisa do que isso dá — e do que não dá:** a colocação
*inicial* é exata por construção (`text[start:end] == anchor` no momento do
render). Isso **não** torna erros de offset impossíveis dali em diante —
toda transformação posterior (mutações §11, fictionalização §7) precisa
preservar ou recalcular os rótulos, e a **validação mecânica final é
obrigatória** para todo registro, sempre (`opf_annotate.py validate` +
invariantes §11). Sequência preferida quando possível:

```text
gerar/mutar conteúdo não rotulado
→ inserir âncoras rotuladas finais
→ registrar offsets
→ validador final
```

Mutações pós-render continuam permitidas, mas só via o contrato de
transformação com edit-map (§11).

O LLM **nunca** decide offsets ou rótulos finais, em nenhuma fase.

## 5. Hard negatives como produto principal de treino

O gerador deve produzir **minimal pairs controlados** — o contraste que
nenhuma coleta passiva fornece de forma balanceada:

```text
Positivo:
Ante o exposto, julgo procedente o pedido.

Negativo:
A sentença recorrida registrou: "Ante o exposto, julgo procedente o pedido."
```

Famílias de negativos obrigatórias (seguem os pontos mais difíceis do
esquema: um único `dispositivo_abertura` operativo; `resultado` só no verbo
operativo; dispositivo individual ≠ decisório colegiado):

- fórmulas de resultado dentro do relatório (descrevendo a sentença anterior);
- resultados citados de precedentes;
- valores monetários que não são `valor_condenacao`;
- "Decido" fora da seção operativa;
- cabeçalhos duplicados (quebra de página);
- frases de ementa dentro de citações;
- "à unanimidade"/"por maioria" fora do decisório colegiado;
- múltiplos "Ante o exposto" com apenas um operativo;
- resultado da instância anterior vs. resultado do recurso atual;
- conclusão de voto individual vs. resultado colegiado;
- ementa sem a palavra "EMENTA"; relatório sem "É o relatório";
- seção `_inicio` sem `_fim` correspondente.

Proveniência explícita e ratio controlável:

```json
{
  "difficulty": "adversarial",
  "hard_negative_families": ["quoted_dispositivo", "reported_prior_outcome"]
}
```

O gerador expõe o ratio positivos/negativos adversariais como parâmetro —
é uma variável experimental (§12, Run D; §16).

## 6. Ancoragem no corpus real

### 6.1 Parquets como distribuição de referência (calibração agregada)

Os `textos.parquet` de produção (IA, `{TRIBUNAL}-{date}-textos.parquet`,
gerados pelo consolidate) calibram o gerador:

- **distribuição estrutural**: frequência real de seções, comprimentos,
  ordem por tribunal/tipo;
- **superfície real**: variantes reais de dispositivo/encerramento/cabeçalho
  mineradas do corpus alimentam `phrase_banks.py` com formas que ocorrem de
  verdade e suas frequências;
- **perfil de ruído real**: artefatos de extração observados calibram
  `noise_profile`.

Distinção importante: **calibração agregada** (estatísticas, contagens,
frequências) pode usar o corpus amplo; **reuso direto de texto** (§6.2)
obedece às invariantes de split do §10 — texto de documentos de
validação/teste jamais aparece em registros de treino.

**Endurecimento explícito:** mesmo a calibração agregada **exclui por hash**
os documentos já identificados como val/test antes de computar qualquer
estatística de `corpus_stats.py` — não porque o texto vaze diretamente (não
vaza), mas para que a alegação "teste travado" seja **inequívoca**: nenhuma
contagem, frequência ou distribuição usada para calibrar o gerador terá sido
influenciada, nem agregadamente, pelos documentos que medem o resultado
final. O filtro por hash de `train_source_doc_ids ∪` (documentos ainda não
atribuídos a nenhum split, se a calibração ocorrer antes do split de um novo
lote de gold) é responsabilidade de `corpus_stats.py`, verificada pelo mesmo
`split_guard.py` do §10.

### 6.2 Registros híbridos (conteúdo real, estrutura sintética)

Trechos reais (fatos/fundamentação) preenchem a camada 2, e o renderer
insere as âncoras. Ganha realismo linguístico — com três salvaguardas:

1. **Origem restrita**: trechos reais só podem vir de **documentos reais de
   treino** (invariante §10.4) — nunca de documentos de validação/teste.
2. **Scrub de âncoras**: texto real pode conter âncoras reais ("ante o
   exposto" numa fundamentação citada) que virariam falsos negativos. Todo
   trecho importado passa por detecção das expressões-âncora e (a) descarte,
   (b) neutralização, ou (c) promoção deliberada a hard negative — nunca
   ignorar. Verificado mecanicamente (`validators.py`).
3. **Fictionalização determinística** (§7) antes do render final.

## 7. Identidades fictícias por padrão

Conforme docs/GOVERNANCE.md, o projeto já tem posição estabelecida sobre
preservação e análise de publicações judiciais oficiais públicas — **PII não
é um bloqueador em aberto** e anonimização **não é requisito legal** para
reuso desse texto. Identidades fictícias nos dados gerados são uma escolha
de **qualidade de dataset e anti-memorização** (o modelo não deve gastar
capacidade memorizando nomes reais irrelevantes para a tarefa), não uma
precaução jurídica, e não são motivo para esconder a linhagem da fonte.

Para registros totalmente sintéticos: partes, advogados, magistrados e
empresas fictícios; números OAB/processo/CPF/CNPJ sintéticos quando
estruturalmente necessários; identidade internamente consistente (gênero,
tratamento, pronomes coerentes ao longo do documento); `identity_seed`
explícito e reprodutível.

Para registros híbridos com trechos reais:

```text
trecho real (de documento de TREINO)
→ substituir identidades reais selecionadas, deterministicamente
→ gerar/preservar conteúdo estrutural
→ inserir âncoras rotuladas
→ registrar offsets finais
```

**Não** substituir indiscriminadamente: citações legais, frases-âncora,
valores monetários rotulados, referências processuais rotuladas, metadados
de tribunal/estilo necessários ao realismo do template.

## 8. LiteLLM como camada de acesso a modelos

Tanto o conteúdo LLM da fase 2 quanto o juiz opcional (§9) usam **LiteLLM**
— já é dependência do projeto (`litellm>=1.40.0`, grupo `classify`) e o
padrão estabelecido em `scripts/annotate_with_llm.py` e
`src/causaganha/analysis/llm_analyzer.py`. Este RFC reusa o padrão
existente, não cria outro:

- model strings `openrouter/<provider>/<model>[:free]`;
- cadeia de fallback + rotação de chaves (`GEMINI_API_KEYS`,
  `OPENROUTER_API_KEY`) herdada de `llm_analyzer.py`;
- `litellm.drop_params = True`;
- gerador e juiz em **famílias de modelo diferentes** quando possível — um
  modelo não valida o próprio estilo de geração.

## 9. Diagnósticos estatísticos primeiro; juiz LLM opcional e subordinado

O juiz LLM **não é requisito** para o treino sintético inicial. Antes dele,
implementar diagnósticos baratos e determinísticos:

- acurácia de um discriminador real-vs-sintético;
- duplicação por vizinho mais próximo / edit distance normalizada;
- divergência de comprimento de documento, ordem de seções, frequência de
  âncoras e vocabulário;
- cobertura por `template_family`; frequência de hard negatives; suporte
  por classe por tipo de fonte.

Interpretação: um discriminador que separa fácil real de sintético é
**evidência diagnóstica, não prova de inutilidade** — exemplos sintéticos
podem diferir intencionalmente e ainda ensinar invariâncias valiosas.
Interpretar junto com o desempenho em validação real.

Quando/se adotado, o juiz LLM: identifica defeitos estilísticos e realimenta
o **gerador** (phrase banks, pesos de `DocumentSpec`, mutações —
`generator_version` incrementa); **nunca** edita rótulos; **nunca** acessa
exemplos do teste travado para seleção do gerador; **nunca** substitui a
validação real; família de modelo distinta do gerador de conteúdo (§8);
execução por subagentes (skill `llm-work-via-subagents`). Veredito
registrado na proveniência (`judge_score`, `judge_version`,
`judged_against`).

## 10. Invariantes anti-vazamento (não negociáveis)

```text
data/segmenter_splits/      # somente gold real pristino (inalterado)
data/segmenter_synthetic/   # gerados: synthetic / hybrid / augmented
```

1. **Split primeiro**: documentos reais pristinos são divididos em
   train/val/test **antes** de qualquer geração ou augmentation.
2. Augmentation só ocorre **depois** do split; o registro aumentado
   **herda o split do documento-pai**.
3. Filhos do mesmo documento-fonte ficam **no mesmo split**.
4. Trechos reais em registros híbridos/sintéticos vêm **somente de
   documentos reais de treino**.
5. **Nenhum texto** de documentos de validação/teste aparece no treino, por
   nenhum caminho.
6. Um documento usado como exemplo de avaliação travada não calibra um
   exemplo de treino por **reuso direto de texto** (calibração agregada
   §6.1 é permitida quando não expõe texto/rótulos de avaliação ao gerador).

Validadores obrigatórios:

```python
train_source_doc_ids & val_source_doc_ids == set()
train_source_doc_ids & test_source_doc_ids == set()
val_source_doc_ids & test_source_doc_ids == set()
```

Mais: hashes de texto normalizado; detecção de quase-duplicatas; IDs de
família de fonte; proveniência por trecho em registros híbridos.

Regras de contagem (herdam §3): `augmented`, `synthetic` e `hybrid` não
contam para G1–G5 e não entram em validação/teste. E permanece proibido o
**ciclo recursivo**: o segmentador não gera nem seleciona os dados de treino
da própria próxima versão.

## 11. Correção de offsets e correção semântica (contrato de transformação)

### 11.1 Contrato de transformação

Toda mutação que altera texto após o render inicial retorna um edit-map:

```python
TransformationResult(
    text=new_text,
    labels=new_labels,   # recalculados via edit-map
    edits=edit_map,
)
```

Invariantes finais, verificadas para **todo** registro (gerado, aumentado ou
híbrido), sempre:

```python
0 <= start < end <= len(text)
text[start:end] == expected_surface
sem spans sobrepostos
categoria permanece semanticamente válida
```

Nota Unicode: **não assumir** que conversão de caixa preserva comprimento
(`ß`→`SS`, ligaturas). Mesmo mutações "triviais" passam pelo contrato.

### 11.2 Correção semântica: um span alinhado ainda pode ser um exemplo ruim

Um offset correto sobre uma âncora corrompida é um positivo inválido.
Classificação das mutações (aplica-se a sinônimos, ruído OCR, remoção de
acentos, substituição Unicode, caixa, pontuação, espaços, quebras dentro de
âncoras):

- **Fora de spans rotulados**: amplamente permitido, sujeito a validação.
- **Dentro de spans rotulados**: permitido apenas via **allowlists por
  categoria** de variantes válidas (na prática: o resultado precisa ser uma
  variante reconhecida em `phrase_banks.py` — o que faz da mutação interna
  uma forma de *alimentar* o phrase bank com variação real, não de gerar
  rótulos livres).
- **Transformações que destroem a âncora**: permitidas somente quando (a) o
  rótulo é removido, (b) a ocorrência vira deliberadamente hard negative, e
  (c) o contexto resultante permanece coerente.

Recurso de sinônimos: **lista jurídica curada, pequena e de alta precisão**
(partindo das variantes de `phrase_banks.py`), nunca tesauro genérico de
PT-BR — `procedente`/`improcedente` são próximos semanticamente e opostos
juridicamente; `sentença`/`acórdão` não são intercambiáveis.

O validador final checa: integridade de offsets; sobreposição; forma de
superfície permitida; compatibilidade semântica categoria↔âncora
transformada.

## 12. Protocolo experimental

### 12.1 Separação seleção/avaliação (regra dura)

```text
Desenvolvimento e seleção de modelo/configuração:
    validação real

Avaliação final:
    teste real TRAVADO
```

**Toda** decisão — design do gerador, phrase banks, perfis de mutação, ratio
sintético/real, curriculum, pesos, hiperparâmetros, parada, filtro do juiz,
alvo de classes — usa **somente validação real**. O teste real permanece
travado até a configuração completa congelar; é avaliado uma vez ao final.

Como o corpus é pequeno no início, são permitidos: cross-validation agrupada
repetida sobre o corpus real não-teste; reamostragem repetida train/val;
agrupamento por tribunal/família documental; test set fixo, travado e
verificado.

### 12.2 Regimes de treino (todos são hipóteses; nenhum é o default)

| Run | Regime | Val/test |
|---|---|---|
| A | somente real pristino (baseline, não o preferido presumido) | real |
| B | pré-treino sintético amplo → fine-tuning real | real |
| C | mistura real+sintético em todo o treino (amostragem configurável) | real |
| D | curriculum adversarial: estrutural amplo → pesado em hard negatives → estágio final real-heavy | real |
| E | real pristino + augmented real (§11) | real |
| F | híbrido (linguagem real de docs de treino + estrutura/identidades sintéticas) | real |
| G | oversampling sintético dirigido a classes raras/confusas (`preliminar_*`, `custas_*`, `honorarios_*`, `voto_*`, `acordao_decisorio_*`, casos difíceis de `resultado`/`dispositivo_abertura`) | real |

Ratios sintético:real explicitamente admitidos: 1:1, 5:1, 10:1 e maiores
quando justificado. **Contagem de documentos não determina sozinha a
influência de cada fonte** — amostragem por fonte, peso na loss, curriculum
e exposição repetida ao real são controles separados (§13).

### 12.3 Justiça experimental

Para cada run, controlar ou reportar: passos de otimizador; tokens totais;
número de exposições ao real pristino; probabilidades de amostragem por
fonte; pesos de loss por fonte; batch size; schedule de LR;
inicialização/checkpoint; seed; estágios de curriculum. Diferenças de
orçamento (ex.: tokens totais) são permitidas quando são **variáveis
experimentais explícitas**, nunca confounders escondidos.

Estatística: preferencialmente 5 seeds, no mínimo 3; média e desvio; 
comparação pareada com o baseline A; intervalos de confiança/bootstrap
quando viável. *Nota de custo:* com os limites empíricos de T4 documentados
no PR #792 (1 época/host-RAM), 7 regimes × 3–5 seeds é orçamento real de
computação — o budget é variável declarada do protocolo, não detalhe.

### 12.4 Métricas — hierarquia pré-declarada, não uma lista plana

Com muitas métricas candidatas, quase todo run "parece bem-sucedido" em
alguma delas depois do fato. Por isso a hierarquia é fixada **antes** de
rodar os experimentos, não escolhida depois olhando os resultados:

1. **Endpoint primário (único, decide aceitação/rejeição por padrão):**
   macro-F1 em validação real.
2. **Endpoints secundários-chave (pré-registrados, não descobertos post-hoc):**
   macro-F1 de classes raras (o subconjunto difícil fixado no item 3); taxa
   de falsos positivos em hard negatives.
3. **Subconjunto de classes difíceis — fixado antes dos experimentos, não
   escolhido depois de ver quais melhoraram:** `preliminar_*`, `custas_*`,
   `honorarios_*`, `voto_*`, `acordao_decisorio_*` (as classes que o RFC
   0001 diagnosticou como inaprendíveis no seed).
4. **Regra de aceitação:** um regime substitui o baseline A quando o
   endpoint primário melhora **e** nenhum secundário-chave regride além de
   uma margem pré-registrada; ou quando o primário fica estável e **algum**
   secundário-chave melhora materialmente, sem regressão nos demais. Fora
   dessas duas condições, não é aceito — "parece bem-sucedido em alguma
   métrica" não é critério.

Métricas exploratórias (reportadas, mas não decidem aceitação): macro-F1
excluindo categorias mecanicamente fáceis; F1 por classe fora do
subconjunto difícil; acurácia de fronteira; confusões específicas (`voto_*`
× `acordao_decisorio_*`; `resultado` operativo × citado/reportado;
`dispositivo_abertura` operativo × citado); desagregação por tribunal, tipo
documental, `template_family`, nível de ruído e contribuição real×sintética;
variância entre seeds; eficiência amostral sobre o real; redução de gold
real anotado necessário para uma meta.

A infraestrutura de comparação (W&B `causaganha-segmenter`, config/lineage
por run) vem do PR #792.

## 13. Mistura e curriculum como controles de primeira classe

```python
TrainingMix(
    pristine_real_weight=4.0,
    augmented_real_weight=2.0,
    synthetic_weight=1.0,
    hybrid_weight=1.0,
)
```

(ou probabilidades de amostragem equivalentes). Curricula candidatos:

- **Synthetic-first**: sintético amplo → sintético adversarial → misto →
  finalização real-heavy;
- **Misto contínuo**: ratio real/sintético fixo ou agendado por batch;
- **Curriculum de classes raras**: estrutura geral → concentração sintética
  nas raras → fine-tuning real;
- **Geração dirigida por falhas**: análise de erros **de validação** →
  identificar família de confusão → gerar sintético direcionado → retreinar
  → reavaliar em validação. Este loop usa erros de validação; **jamais** o
  teste travado para iteração do gerador.

## 14. Fases de implementação

O **gerador estrutural é o produto principal** e tem prioridade conceitual.
A augmentation mecânica é complementar — útil e barata, mas seu resultado
não prevê o valor da geração estrutural (ensinam coisas diferentes: ruído
vs. estruturas raras/hard negatives), então nada "espera para ver se o regex
ajuda".

**Foundation PR (pequeno, habilitador):** infraestrutura de correção
compartilhada — validador de split por família de fonte (§10); validador
final de spans (§11.1); contrato de transformação/edit-map; schema de
proveniência (§15); detecção de duplicatas e quase-duplicatas.

**Fase 1 — gerador estrutural determinístico (implementação principal):**
`DocumentSpec`; renderer determinístico; famílias de template
sentença/acórdão; phrase banks; gerador de identidades fictícias (§7);
geração de hard negatives (§5); proveniência estrutural; calibração por
`corpus_stats` (§6.1); integração com val/test reais; export direto para
JSONL treinável. **Sem LLM.**

**Fase 1-bis — augmented real (complementar):** augmentation controlada de
registros reais de treino usando a mesma infraestrutura de
transformação/proveniência. Sinônimos dependem da lista curada
(`phrase_banks.py`) existir.

**Fase 2 — híbrido e conteúdo LLM:** trechos de linguagem real (documentos
de treino, §6.2); fictionalização determinística (§7); conteúdo de seção
gerado por LLM (§8); variação de estilo mais ampla.

**Fase 3 — juiz LLM opcional e melhoria automatizada do gerador:** somente
depois de os diagnósticos estatísticos baratos (§9) existirem.

Layout de módulos:

```text
scripts/generate_synthetic_segmenter.py
scripts/synthetic_segmenter/
    specs.py            # DocumentSpec + amostragem com seed
    renderer.py         # âncoras + offsets iniciais por construção
    phrase_banks.py     # variações por categoria + sinônimos curados
    identities.py       # identidades fictícias determinísticas (identity_seed)
    hard_negatives.py   # famílias de negativos + ratio controlável
    corpus_stats.py     # calibração agregada dos textos.parquet
    transform.py        # contrato TransformationResult/edit-map (Foundation)
    augment_real.py     # fase 1-bis: augmentation de gold de treino
    split_guard.py      # invariantes anti-vazamento §10 (Foundation)
    validators.py       # invariantes finais §11 + scrub de âncoras
    diagnostics.py      # §9: discriminador, divergências, duplicação
    llm_content.py      # fase 2: conteúdo interno via LiteLLM
    llm_judge.py        # fase 3: juiz opcional via LiteLLM
    compose_mix.py      # §15-bis.3: TrainingMix -> train.jsonl materializado
tests/test_synthetic_segmenter.py
```

## 15. Categorias de proveniência

Quatro categorias, no mínimo:

| Categoria | Descrição |
|---|---|
| **Pristine real** | gold verificado manualmente |
| **Augmented real** | filho transformado de um documento real pristino de treino |
| **Fully synthetic** | gerado de specs/phrase banks/LLM, sem trecho real direto |
| **Hybrid synthetic** | estrutura sintética contendo trechos reais de documentos de treino |

```json
{
  "source_type": "hybrid_synthetic",
  "synthetic": true,
  "augmented": false,
  "contains_real_text": true,
  "source_doc_ids": ["tjro_acordao_0017"],
  "entities_fictionalized": true,
  "generator_version": "v2",
  "template_family": "tjro_acordao_moderno",
  "seed": 123,
  "identity_seed": 456,
  "difficulty": "adversarial",
  "hard_negative_families": ["quoted_result"]
}
```

A proveniência existe para: reprodutibilidade, auditabilidade, enforcement
de split, detecção de duplicatas, debugging, avaliação por fonte e ablation
do gerador — não primariamente como salvaguarda de privacidade.

O manifest separa contagens por categoria
(`real_documents`/`synthetic_documents`/`augmented_documents`/
`hybrid_documents` e suporte por classe por fonte).

## 15-bis. Armazenamento e uso em treino

O RFC até aqui especifica *como gerar* dados sintéticos; esta seção
especifica *onde eles vivem* e *como o treino de fato os consome* — uma
lacuna real do desenho original, porque o resto do pipeline (gates,
`opf_annotate.py`, os drivers do PR #792) só sabe lidar com arquivos
concretos em caminhos concretos.

### 15-bis.1 Decisão de armazenamento: regenerar vs. persistir

Nem toda categoria de dado sintético tem o mesmo custo de armazenamento,
porque nem toda categoria é igualmente reproduzível:

- **Fully synthetic sem LLM (fase 1)** é **determinístico por construção**
  — `generator_version` + `seed` + `DocumentSpec` reproduzem exatamente o
  mesmo JSONL. Para este caso, **não persistir o corpus gerado como
  artefato versionado**: persistir o gerador (código, `phrase_banks.py`,
  git-tracked) e um manifest pequeno de quais seeds/specs compõem cada
  "release" nomeado. O JSONL é materializado sob demanda no momento do
  preparo de dados — igual, em espírito, ao modo `--bootstrap` que
  `prepare_privacy_filter_dataset.py` já tem para gerar a partir de
  parquet.
- **Fase 2 (conteúdo LLM, híbrido, filtrado por juiz) não é perfeitamente
  reproduzível** (mesma seed, chamada de LLM diferente ⇒ texto diferente).
  Aqui o artefato gerado **precisa ser persistido** como dado durável, do
  mesmo jeito que o gold: versionado, com hash, nunca regenerado
  silenciosamente sob o mesmo `generator_version`.
- **Augmented real** (§11) é determinístico dado o documento-fonte + a
  seed de mutação — mesmo tratamento de "regenerar sob demanda" da fase 1,
  desde que o documento-fonte (gold) não mude.

Em nenhum caso o corpus sintético/aumentado/híbrido de tamanho não-trivial
é **commitado no git** — seguindo a convenção já estabelecida no projeto
(CLAUDE.md: não gerar caches a partir de fontes aleatórias; dado derivado
grande vive fora do git). Git guarda gerador, phrase banks, lista de
sinônimos curada e manifests pequenos; nunca o JSONL de centenas de MB.

### 15-bis.2 Onde persistir o que precisa ser persistido — Kaggle E IA, não um ou outro

**Decisão fixada:** todo `generator_version` que precisa ser persistido
(§15-bis.1 — fase 2/LLM, híbrido) é escrito em **dois lugares**, não um com
o outro como alternativa:

- **IA (Internet Archive) é a fonte de verdade de longo prazo.** Consistente
  com a missão de arquivo do projeto (docs/GOVERNANCE.md) e com a
  convenção já estabelecida para outros dados do projeto (CLAUDE.md: itens
  DJEN usam `djen-{tribunal}-{year}`). Para o corpus sintético, item
  próprio por versão do gerador:
  `causaganha-segmenter-synthetic-{generator_version}` (ex.:
  `causaganha-segmenter-synthetic-v2`), contendo o(s) JSONL por categoria
  (`synthetic.jsonl`, `hybrid.jsonl`, `augmented.jsonl`) + o manifest de
  proveniência (§15). Upload via `httpx`, não `boto3` — mesma regra de
  `archive.py`/CLAUDE.md que já vale para os outros uploads do projeto.
  Permanente, fora do controle de uma conta Kaggle/Colab pessoal, alinhado
  com "preservação integral" (GOVERNANCE.md §5).
- **Kaggle Dataset privado é o cache operacional** usado pelos drivers de
  treino. Publicado a partir do item do IA (não editado independentemente —
  o IA é a fonte, o Kaggle Dataset é derivado), versionado
  (`kaggle datasets create`/`version`, mesmo fluxo de `train_on_kaggle.sh`),
  em dataset **separado** dos gold splits
  (`causaganha-segmenter-synthetic`) — mantém a fronteira
  pristine-real/gerado visível na própria organização de datasets, não só
  no JSON de proveniência.
- **Colab:** para corpora pequenos, `colab upload` direto a partir do
  mesmo cache; para corpora grandes (o caso esperado em ratios 5:1/10:1),
  cache no Google Drive — o mesmo padrão de "base model uma vez, artefato
  por run" já descrito na skill `opf-finetune`
  (`references/colab-and-drive.md`) para o checkpoint base, aplicado agora
  ao corpus de treino. A cópia do Drive também deriva do item do IA.

Fluxo de escrita: gerador produz o JSONL localmente → upload para o item do
IA (fonte de verdade) → publica/atualiza o Kaggle Dataset e (se necessário)
o cache do Drive a partir do que acabou de subir no IA. Nunca o inverso —
nenhum cache operacional é editado sem o IA já ter a versão correspondente.

### 15-bis.3 Composição do mix de treino — o ponto de integração real

O CLI do `opf` (`opf train train.jsonl --validation-dataset val.jsonl
--label-space-json ... --output-dir ...`) aceita como argumento posicional
um **path ou glob** de JSON/JSONL — verificado no código-fonte de
`opf/_train/args.py` (`dataset`: "Local train dataset path or glob
(JSON/JSONL(.gz))"), não um único arquivo obrigatório como uma leitura
apressada do wrapper sugeriria. Isso significa que múltiplos arquivos *são*
suportados nativamente — mas só como **pool concatenado com peso igual por
exemplo**; não há flag de ratio/peso por fonte no parser. Um glob resolveria
"treinar em tudo que existe", não "4x pristine real para cada 1x sintético".
Logo, o `TrainingMix` do §13 (pesos por fonte, curriculum) continua sendo
algo que o `opf` não entende nativamente — é um **passo de composição que
roda antes dele**, produzindo um único `train.jsonl` materializado com a
mistura desejada já embutida (por repetição/amostragem conforme os pesos),
exatamente como o pipeline já faz hoje com um único `train.jsonl` pristino.

Isso é `compose_mix.py`, já listado no layout de módulos do §14. Ele lê os
pools (pristine real de `data/segmenter_splits/`, augmented/synthetic/hybrid
de onde estiverem — regenerados ou baixados
conforme §15-bis.1/.2), aplica os pesos/curriculum do §13, e escreve um
`train.jsonl` + um **manifest do mix** (não confundir com o manifest de
proveniência por documento do §15):

```json
{
  "mix_id": "run_D_seed_3_epoch_config_v1",
  "generator_version": "v2",
  "weights": {"pristine_real": 4.0, "augmented_real": 2.0,
              "synthetic": 1.0, "hybrid": 1.0},
  "curriculum_stage": "adversarial_heavy",
  "counts_by_source_type": {"pristine_real": 150, "synthetic": 750},
  "source_doc_ids_pristine_real": ["..."]
}
```

`val.jsonl`/`test.jsonl` **nunca** passam por `compose_mix.py` — permanecem
exatamente os arquivos pristinos reais de `data/segmenter_splits/`, sem
exceção (§12.1).

O `train.jsonl` composto entra no pipeline dos drivers do PR #792
(`train_on_colab.sh`/`train_on_kaggle.sh`, `opf_shared.train_and_eval`) sem
nenhuma mudança de assinatura — eles já esperam `DATA/train.jsonl` como um
arquivo; `compose_mix.py` só decide o que vai dentro dele. A lineage já
existente nesses drivers (`input_sha256` por arquivo, logado no config do
run do W&B) se estende naturalmente: o hash do `train.jsonl` composto entra
como mais uma entrada, e o **manifest do mix acima é logado junto**, para
que todo run no W&B seja rastreável até a composição exata (pesos, versão
do gerador, seeds) que o produziu — não só até o hash de um arquivo opaco.

### 15-bis.4 Retenção e versionamento

- **Fase 1 determinística**: sem política de retenção necessária — é
  regenerável a qualquer momento a partir do git; "descartar" uma versão
  antiga é só não referenciá-la mais.
- **Fase 2 / híbrido (persistido)**: manter um dataset/versão por
  `generator_version` usado em algum run reportado (para auditar
  resultados publicados); `generator_version`s claramente superadas e sem
  run associado podem ser removidas depois de um período — critério exato
  fixado em §16.1, item 10.

## 16. Decisões e processo de fechamento

Nenhuma questão fica em aberto sem resposta. Para escolhas de engenharia,
a resposta é a decisão em si. Para escolhas que dependem de dado empírico
que só os experimentos do §12 produzem, a resposta é o **procedimento de
decisão + o ponto de partida concreto** — fechar a questão não significa
inventar um número sem tê-lo medido; significa que não há mais um "?" solto,
há um plano determinístico para chegar à resposta.

### 16.1 Fechadas por decisão de engenharia (efetivas já na fase 1/Foundation)

1. **Amostragem por fonte vs. peso na loss** → **amostragem por fonte**, em
   `compose_mix.py`. `opf train` não expõe peso por exemplo/loss (verificado
   em `opf/_train/args.py`, §15-bis.3); amostragem na composição é a única
   via nativa e a mais simples de auditar.
2. **Cobertura de estilos de tribunal** → fase 1 cobre **somente TJRO**
   (único tribunal com gold hoje). `template_family` faz o design já
   comportar extensão, mas nenhum template de STJ/outro TJ é construído
   antes de existir gold real desse tribunal para calibrar e validar contra
   (§3 — real audita a ontologia; sintético não define estrutura que o real
   nunca confirmou).
3. **Gerar `_inicio` sem `_fim` deliberadamente** → **sim**, incluído como
   família própria de hard negative (§5), não como erro: um `_inicio` órfão
   sem seu par é exatamente o "sinal de qualidade de dados" que o esquema
   de pareamento já usa para detectar problemas reais de anotação — o
   gerador deve ensinar o modelo a não assumir que todo `_inicio` implica
   um `_fim` próximo. Proporção inicial: 1 em cada ~10 documentos que têm a
   seção, ajustável por `DocumentSpec`.
4. **Grau de ruído de extração** → não é escolha livre: **usa a distribuição
   real observada em `corpus_stats.py`** (§6.1), não um valor arbitrário. A
   pergunta original presumia uma escolha que o RFC já delega à calibração.
5. **Cadência de recalibração do gerador** → **orientada a evento, não a
   tempo**: recalibra sempre que um novo lote de gold real é anotado e
   mesclado em `data/segmenter_splits/` — mesmo gatilho que já existe no
   fluxo de anotação, sem cadência fixa adicional para manter.
6. **Comprimento de trecho híbrido** → **nível de seção** (um parágrafo
   inteiro de fundamentação/relatório, não frase isolada nem documento
   completo). Frase isolada perde contexto estrutural; documento completo
   reintroduz o risco de âncora-real-não-escrubada em excesso de superfície
   de uma vez. Seção é o grão que a arquitetura já usa (§4.1, `sections`).
7. **Active learning** → **sim**, extensão do mesmo loop de geração dirigida
   por falhas (§13): erros de validação real não só disparam sintético
   direcionado, também **priorizam quais documentos reais anotar a
   seguir** — mesma análise de erro, duas saídas.
8. **Escopo do `transform.py`** → **utilitário genérico de edit-map**, não
   funções por tipo de mutação. A lógica de deslocamento de offset é
   idêntica independente do tipo de mutação (só a transformação de string
   muda); um utilitário único, bem testado uma vez, com funções finas por
   tipo de mutação chamando-o — menos superfície para o mesmo bug de offset
   reaparecer em cada mutação nova.
9. **Limiar de tamanho git vs. externo** (§15-bis.1) → **nenhum corpus
   sintético/aumentado/híbrido de tamanho não-trivial vai para o git**,
   ponto — a distinção não é um limiar de tamanho, é a distinção
   determinístico-regenerável (fase 1, nunca persistido como arquivo, só
   como manifest de seeds) vs. não-reproduzível (fase 2+, sempre
   persistido no IA desde o primeiro registro, §15-bis.2). Refinamento
   possível depois: cachear localmente builds de fase 1 que demorem mais
   que ~1 minuto para regenerar, como otimização de performance — nunca
   como fonte de verdade.
10. **Critério de retenção de `generator_version` persistidas**
    (§15-bis.4) → mantida enquanto **qualquer run reportado no W&B
    referenciar essa `generator_version`** no config (lineage já existente,
    §15-bis.3); elegível para remoção do Kaggle Dataset/Drive quando (a)
    nenhum run ativo/recente a referencia **e** (b) uma `generator_version`
    mais nova a superou há mais de 90 dias. **O item do IA nunca é
    removido** — é o arquivo permanente (§15-bis.2); só os caches
    operacionais (Kaggle/Drive) são elegíveis para limpeza.

### 16.2 Fechadas por procedimento empírico (ponto de partida definido; resposta final vem do §12)

11. **Ratio sintético:real ótimo** → não decidível a priori. Ponto de
    partida: começar em **1:1 e 5:1** como os dois primeiros pontos da
    curva (Runs C/G), 10:1+ só se 5:1 continuar melhorando os
    secundários-chave (§12.4) sem regredir o primário. Fechada quando os
    Runs B/C/D/G do §12.2 produzirem a curva ratio×métrica.
12. **Pré-treino sintético vs. mistura contínua** (Run B vs. C) → começar
    por **C (mistura contínua)** — infraestrutura mais simples
    (`compose_mix.py` de passo único vs. treino em dois estágios) — e só
    investir em B se C não atingir o endpoint primário. Fechada pela
    comparação direta B vs. C no protocolo.
13. **Duração do estágio final real-heavy** no curriculum adversarial
    (Run D) → ponto de partida: **últimos 20% dos passos de otimizador**
    são real-only ou real-dominante; ajustado empiricamente pela curva de
    validação do Run D (regride se o estágio for curto demais para
    "reancorar" no real, satura se longo demais para diluir o ganho
    adversarial).
14. **Contagem alvo por classe rara** antes de saturar (Run G) → ponto de
    partida ancorado num número que já existe no projeto: `_GATE_MIN_TRAIN_SUPPORT`
    (10 spans/categoria, o mínimo do gate G2) é o piso absoluto para gold
    real; para sintético o ponto de partida é **10× esse piso (100
    exemplos/categoria rara)**, escalado por classe conforme a curva de
    recall do Run G saturar ou não.
15. **Ratio hard-negative/positivo** por família de negativo → ponto de
    partida **1:1** (prática comum em treino adversarial), ajustado por
    família conforme a taxa de falsos positivos daquela família específica
    no Run D/relatório de erro (§13).
16. **Quais falhas de validação disparam geração sintética dirigida** (§13)
    → taxonomia fixada, não mais em aberto: (a) recall de uma classe rara
    abaixo do alvo do item 14; (b) taxa de FP em hard negatives de uma
    família específica acima de um limiar (a fixar empiricamente no
    primeiro Run D — não há dado ainda para cravar o número); (c) confusão
    sistemática entre duas classes específicas (ex.: `voto_*` ×
    `acordao_decisorio_*`) acima da taxa de base do Run A. Cada gatilho
    mapeia para uma família de geração dirigida correspondente.
17. **Amostragem dos parquets para `corpus_stats`** → **estratificada por
    tribunal/período**, mesmo princípio já mandado para anotação pela
    skill `opf-finetune` (evita overfit a um formato/época). Na prática,
    hoje **degenera para TJRO-only** porque é o único tribunal com dado —
    a estratificação passa a ter efeito real assim que um segundo tribunal
    entrar no corpus, sem precisar mudar o código quando isso acontecer.
