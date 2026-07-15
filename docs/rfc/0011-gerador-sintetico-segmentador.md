# RFC 0011 — Gerador sintético estrutural para o Decision Segmenter

- **Status:** Proposto
- **Data:** 2026-07-15
- **Relacionado:** RFC 0001 (diagnóstico do fine-tuning v7), ADR 0010 (Rebuild
  Segmenter Pipeline v7), PR #792 (treino headless Colab/Kaggle)
- **Escopo:** geração de dados sintéticos de treino para o segmentador de
  decisões (OPF, âncoras BIOES) — arquitetura do gerador, hard negatives,
  separação gold/sintético, protocolo experimental e escopo de primeira
  implementação.

## 1. Resumo executivo

É tecnicamente viável — e particularmente adequado a este segmentador —
aumentar o corpus de treino com documentos sintéticos, porque o modelo não
tenta compreender a decisão inteira: ele aprende **âncoras curtas e
fronteiras estruturais** (`ementa_inicio`, `resultado`, `voto_inicio`,
`acordao_decisorio_fim`, ...). O guideline atual privilegia explicitamente
cues de 1–5 palavras e offsets mecânicos, não anotação de parágrafos.

A proposta central: **não** gerar "uma sentença completa com rótulos" num
único prompt de LLM. Em vez disso, um **gerador híbrido estrutural** em três
camadas, onde o programa (não o LLM) controla estrutura, âncoras e offsets:

1. um **plano abstrato** (`DocumentSpec`) decide tipo, seções, resultado e
   perfil de ruído;
2. conteúdo interno das seções pode vir de LLM (fase 2) ou de phrase banks
   gramaticais (fase 1), sem poder de decisão sobre rótulos;
3. um **renderer determinístico** insere as âncoras e registra os offsets no
   momento da inserção — `text[start:end]` é garantidamente igual ao anchor,
   como o guideline exige.

O valor real está nos **hard negatives** (a mesma expressão aparecendo onde
NÃO deve ser marcada) e no reforço das classes estruturalmente raras
(`preliminar_*`, `custas_*`, `honorarios_*`, `voto_*`,
`acordao_decisorio_*`) — exatamente as que o RFC 0001 diagnosticou como
inaprendíveis no seed atual. Sintético **nunca** conta para os gates G1–G5
nem entra em validação/teste.

O gerador é ancorado no corpus real que o projeto já coleta: os
`textos.parquet` de produção calibram a distribuição estrutural, os phrase
banks e o perfil de ruído (§4-bis.1), e um **juiz LLM** compara documentos
sintéticos com reais para realimentar o gerador — nunca os rótulos, e nunca
como substituto do critério de aceitação no teste real (§4-bis.2).

Uma terceira técnica, mais barata e mais segura que gerar do zero: **aumentar
por regex os próprios documentos gold reais já anotados** (capitalização,
espaçamento, sinônimos fora dos spans rotulados — §4-bis.4), preservando os
offsets. Não exige LLM na versão base, é o experimento de menor custo do
protocolo (§7, Run E) e serve como fase 0 antes mesmo do gerador estrutural.

## 2. Contexto e motivação

O RFC 0001 diagnosticou três problemas que invalidariam um treino sério com
o seed atual: `preliminar_*` só existe no test set; o val set cobre 17/25
categorias; e o volume (20 docs, 189 spans, 1 tribunal) dá variância enorme
a qualquer F1. Os gates G1–G5 (em `prepare_privacy_filter_dataset.py`)
bloqueiam corretamente o treino real até o corpus escalar.

Escalar o gold real é o caminho principal e continua obrigatório — o ADR
0010 afirma que `voto_*`/`acordao_decisorio_*` precisam de acórdãos
genuínos. Mas a coleta+anotação de gold é lenta, e as classes raras são
raras *estruturalmente* (uma decisão tem no máximo um `acordao_decisorio_*`;
muitas não têm preliminar nem capítulo de custas). Um gerador sintético pode
aumentar a exposição do modelo a essas estruturas **enquanto** o gold real
escala, sem contaminar a medição.

A literatura de legal NLP indica que augmentação generativa ajuda em regime
de poucos dados, mas que paráfrase simples não captura a complexidade da
linguagem jurídica — diversidade contextual e geração condicionada importam.
Também é conhecido o risco de colapso ao treinar recursivamente em dados
sintéticos: misturar continuamente dados humanos reais é a proteção
essencial. Este RFC incorpora ambas as lições como restrições de design
(§6, §7).

## 3. Arquitetura do gerador

### 3.1 Camada 1 — plano abstrato (`DocumentSpec`)

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

O plano controla: sentença vs. acórdão; presença e ordem das seções;
decisão monocrática vs. colegiada; preliminares; honorários e custas;
valores; presença de ementa/relatório/voto/encerramento; variações
tipográficas e ruído de extração. Amostragem com seed explícito.

### 3.2 Camada 2 — conteúdo interno (sem poder sobre rótulos)

O conteúdo factual/argumentativo de cada seção é preenchido **sem decidir
rótulos e sem tocar em offsets**:

```json
{
  "facts": "A autora afirma que...",
  "preliminary_reasoning": "A alegação de cerceamento...",
  "merits_reasoning": "Os documentos demonstram...",
  "holding": "dar parcial provimento ao recurso"
}
```

Requisitos do conteúdo: partes fictícias; números processuais sintéticos;
valores amostrados; áreas jurídicas variadas; estilos de redação e níveis
de formalidade diferentes.

Na **fase 1**, este conteúdo vem de phrase banks gramaticais (sem LLM). Na
**fase 2**, um LLM gera o conteúdo interno — mas as âncoras e os labels
permanecem sob controle determinístico do renderer.

### 3.3 Camada 3 — renderer determinístico

O programa, não o LLM, escolhe e posiciona as âncoras (`EMENTA:`,
`RELATÓRIO`, `É o relatório.`, `VOTO`, `Ante o exposto`, `dou parcial
provimento ao recurso`, `ACORDAM os Desembargadores...`, `à unanimidade.`,
`Publique-se.`), registrando cada offset no momento da inserção:

```python
start = len(buffer)
buffer.append("Ante o exposto")
end = len(buffer)
labels.append({"category": "dispositivo_abertura", "start": start, "end": end})
```

Assim `text[start:end] == anchor` por construção — a classe de bug nº 1 da
anotação (offsets desalinhados) é impossível.

## 4. Hard negatives — onde está o valor

Documentos "perfeitos" e previsíveis produziriam um modelo frágil. O gerador
deve criar situações em que a expressão-âncora aparece mas **não** deve ser
marcada — seguindo exatamente os pontos mais difíceis do esquema atual
(um único `dispositivo_abertura` operativo; `resultado` só no verbo
operativo; distinção entre dispositivo individual e decisório colegiado):

- jurisprudência citada contendo "ante o exposto";
- voto que reproduz o resultado da sentença recorrida;
- vários valores monetários, mas só um `valor_condenacao`;
- "julgo procedente" dentro do relatório, descrevendo a sentença anterior;
- "Decido" no início do mérito (não é `dispositivo_abertura`);
- dois votos, mas somente um decisório colegiado;
- ementa sem a palavra literal "EMENTA";
- relatório sem "É o relatório";
- seção iniciada sem o `_fim` correspondente;
- "por maioria" / "à unanimidade" dentro de citações;
- cabeçalhos repetidos por quebra de página.

## 4-bis. Ancoragem no corpus real (parquets) e juiz LLM

Duas extensões que amarram o gerador à distribuição real em vez de deixá-lo
inventar um "estilo de gerador" próprio. Ambas usam ativos que o projeto já
tem: os `textos.parquet` de produção no Internet Archive
(`{TRIBUNAL}-{date}-textos.parquet`, gerados pelo consolidate — o prep
script já tem um modo bootstrap que lê parquet) e a infraestrutura de
subagentes LLM da anotação.

### 4-bis.1 Parquets reais como distribuição de referência

Em vez de calibrar phrase banks e `DocumentSpec` "de cabeça", extrair
estatísticas do corpus real:

- **distribuição estrutural**: frequência real de seções (quantas decisões
  têm preliminar? capítulo de custas? voto vencido?), comprimentos típicos
  por seção, ordem das seções por tribunal/tipo;
- **superfície real**: variantes reais de abertura de dispositivo, fórmulas
  de encerramento, formatos de cabeçalho — minerados do corpus, não
  inventados (alimentam os phrase banks §5.2 com formas que ocorrem de
  verdade e suas frequências);
- **perfil de ruído real**: os artefatos de extração do DJEN observados
  (quebras, hifenização, Unicode) calibram `noise_profile` em vez de
  mutações arbitrárias.

**Variante "conteúdo real, estrutura sintética":** preencher a camada 2 com
trechos reais dos parquets (fatos/fundamentação reais) e deixar o renderer
inserir as âncoras. Ganha realismo linguístico de graça — mas exige uma
salvaguarda obrigatória: **texto real pode conter âncoras reais** ("ante o
exposto" no meio de uma fundamentação citada), que virariam rótulos ausentes
(falso negativo de treino). Todo trecho real importado passa por um scrub:
detectar ocorrências das expressões-âncora no trecho e (a) descartar o
trecho, (b) neutralizá-lo, ou (c) promovê-lo deliberadamente a hard negative
(§4) — nunca ignorar. O validador (§8 `validators.py`) verifica isso
mecanicamente.

### 4-bis.2 Juiz LLM comparando sintético vs. real

Um passo de julgamento discriminativo entre a geração e o treino: pares
(documento sintético, documento real do parquet de mesmo tipo/tribunal) são
apresentados a um juiz LLM que responde, por dimensão — plausibilidade
estrutural, registro/formalidade, vocabulário jurídico, artefatos de
geração ("cheiro de sintético") — onde o sintético diverge do real.

- **O veredito melhora o GERADOR, não os rótulos**: feedback vira ajuste de
  phrase banks, pesos do `DocumentSpec` e perfis de mutação
  (`generator_version` incrementa). O juiz nunca toca em offsets/labels,
  que permanecem do renderer por construção.
- **Filtro barato, não critério de aceitação**: documentos que o juiz marca
  como flagrantemente irreais podem ser descartados antes do treino, mas o
  critério final continua sendo o §7 — sintético só é mantido quando
  melhora o teste real. O juiz reduz o custo de chegar lá; não substitui a
  medição.
- **Sem ciclo com o segmentador**: o juiz é um LLM generalista comparando
  texto, não o segmentador avaliando os próprios dados de treino — a regra
  §6.3 permanece intacta.
- **Execução por subagentes** (um por lote/dimensão de julgamento), conforme
  a skill `llm-work-via-subagents`, com os erros do juiz decorrelacionados
  do gerador (prompts/framings distintos), no mesmo espírito do ensemble de
  verificação da anotação gold.

Registrar o veredito na proveniência (§6):

```json
"info": {
  "judge_score": {"estrutura": 0.9, "registro": 0.7, "vocabulario": 0.8},
  "judge_version": "v1",
  "judged_against": "TJRO-2025-03-14-textos"
}
```

### 4-bis.3 LiteLLM como camada de acesso a modelos

Tanto o conteúdo de LLM da fase 2 (§3.2) quanto o juiz (§4-bis.2) usam
**LiteLLM** como camada de abstração de provedor — já é dependência do
projeto (`litellm>=1.40.0`, grupo `classify`) e já é o padrão estabelecido
em `scripts/annotate_with_llm.py` (anotação assistida por LLM) e
`src/causaganha/analysis/llm_analyzer.py`. Este RFC não introduz um novo
padrão de acesso a LLM — reusa o existente:

- **Convenção de model string**: `openrouter/<provider>/<model>[:free]`
  (ex.: `openrouter/google/gemma-3-27b-it:free`), igual ao
  `annotate_with_llm.py`;
- **Cadeia de fallback + rotação de chave**: `llm_analyzer.py` já implementa
  fallback entre modelos (Gemini → OpenRouter free-tier) e rotação de
  múltiplas chaves via `GEMINI_API_KEYS`/`GEMINI_API_KEY`,
  `OPENROUTER_API_KEY` — o juiz herda essa resiliência em vez de reimplementar
  retry próprio, relevante porque o volume de pares julgados (§4-bis.2) é
  maior que o de anotação;
- **`litellm.drop_params = True`** para tolerar parâmetros específicos de
  modelo sem quebrar entre provedores, igual ao script existente;
- Modelos do gerador (fase 2, §3.2) e do juiz (§4-bis.2) devem ser
  **famílias diferentes** quando possível (o mesmo raciocínio da
  decorrelação de erros do juiz, §4-bis.2) — um modelo não deve validar o
  próprio estilo de geração.
- Custo/limite de requisições por rodada de geração+julgamento é uma
  variável de execução (via LiteLLM's usage tracking), não uma decisão de
  arquitetura — mas informa a questão em aberto §10.7 (amostragem do juiz).

### 4-bis.4 Aumento por regex de documentos reais (categoria "augmented")

Uma terceira fonte de dados, mais barata que a geração completa (§3): em vez
de sintetizar um documento novo, **perturbar mecanicamente um documento gold
real já anotado** — capitalização, quebras de linha/espaçamento, sinônimos
— preservando a estrutura e o conteúdo real. Não exige LLM na versão base
(regex + tabela de sinônimos); pode ganhar uma variante assistida por LLM
depois, reusando a camada §4-bis.3.

**A restrição que domina o design: toda mutação precisa preservar ou
recalcular os offsets dos spans já anotados.** Isso é mais rígido do que a
mutação de documentos sintéticos (§5.2), onde o renderer ainda não fixou o
texto final — aqui o documento **já tem** `label: [{category, start, end}]`
corretos contra o texto original, e a mutação não pode invalidá-los:

- **Capitalização** (upper/lower/title): preserva o comprimento da string
  — offsets intocados, mutação trivialmente segura.
- **Quebras de linha / espaçamento** (colapsar espaços duplos, inserir
  quebra de página, normalizar `\r\n`): muda o comprimento — a função de
  mutação precisa retornar não só o texto novo mas o **delta de deslocamento
  por posição**, e todo offset após o ponto de mutação é recalculado. Isto é
  trabalho novo — `opf_annotate.py` hoje só valida offsets, não os desloca
  (confirmado antes de escrever esta seção); `mutations.py` (§8) precisa
  desse utilitário de shift, compartilhado entre a mutação de texto
  sintético (§5.2) e a de texto real (aqui).
- **Sinônimos**: a mutação mais perigosa das três, por duas razões
  independentes:
  1. **muda o comprimento** (mesmo tratamento de shift acima);
  2. **pode corromper a própria âncora que o modelo precisa aprender.**
     Trocar uma palavra *dentro* de um span rotulado só é seguro se o
     resultado for uma variante reconhecida da âncora (i.e., já listada em
     `phrase_banks.py`, §5.2) — caso contrário o rótulo aponta para um texto
     que não é mais um exemplo válido da categoria. **Regra padrão: sinônimo
     só troca palavras *fora* dos spans rotulados** (na região não anotada
     do documento). Trocar *dentro* de um span é um modo avançado opcional,
     só permitido quando o resultado é verificado contra `phrase_banks.py`
     — na prática, uma forma de *alimentar* o phrase bank a partir de
     variação real, não de gerar rótulos novos livremente.
  3. Requer um **recurso de sinônimos jurídicos controlado**, não um
     tesauro genérico de PT-BR: termos jurídicos frequentemente parecem
     sinônimos superficiais mas não são intercambiáveis (`procedente` /
     `improcedente` não são sinônimos apesar de semanticamente próximos;
     `sentença` e `acórdão` não são intercambiáveis apesar de ambos serem
     "decisões"). O recurso inicial deve ser uma lista curada pequena e de
     alta precisão (formas de dispositivo, conectivos, verbos de decisão já
     presentes em `phrase_banks.py`), não uma biblioteca de sinônimos de
     propósito geral.

**Proveniência — categoria própria, nem `synthetic` nem gold puro:**

```json
{
  "text": "...",
  "label": [...],
  "info": {
    "id": "augmented_tjro_000017_v3",
    "source_doc_id": "tjro_gold_000017",
    "synthetic": false,
    "augmented": true,
    "augmentation": ["case_upper", "whitespace_collapse", "synonym_outside_span"],
    "augmentation_seed": 20394
  }
}
```

**Regras de contagem, herdadas do §6 sem exceção:** `augmented` **não**
conta para os gates G1–G5 (só o documento-fonte pristino conta — do
contrário volume se ganha de graça, mecanicamente, sem novo dado real) e
**não** entra em validação/teste (mesmo risco de otimismo espúrio que o
sintético — o modelo aprenderia a sobreviver ao próprio estilo de
augmentation). `augmented` fica no mesmo compartimento de treino que
`synthetic`, sujeito ao mesmo protocolo de aceitação do §7.

**Por que vale a pena mesmo sendo mais restrito que a síntese completa:**
o conteúdo é 100% real (herda a distribuição de linguagem/estrutura sem
risco de "cheiro de sintético", diferente de §3), então é um ponto de
partida mais barato e mais seguro que a geração completa — plausivelmente
uma **fase 0**, antes até do gerador estrutural, já que reaproveita
diretamente os 20 documentos gold existentes e o tooling de validação de
offset que este RFC já precisa construir para §4-bis.1.

## 5. Perfis documentais e variação de superfície

### 5.1 Famílias mínimas

**Sentenças:** cível tradicional; Juizado Especial; execução fiscal;
previdenciária; (trabalhista, se o escopo ampliar); curta sem relatório;
extinção sem mérito; homologação; procedência parcial; capítulos separados
de mérito/custas/honorários.

**Acórdãos:** ementa moderna estruturada; antigo em texto corrido; Turma
Recursal; unânime; por maioria; voto vencido; preliminar + mérito; acórdão
que apenas mantém a sentença; voto longo + decisório curto; múltiplos votos.

### 5.2 Phrase banks e mutações

```python
DISPOSITIVO_OPENINGS = [
    "Ante o exposto", "Diante do exposto", "Pelo exposto",
    "Posto isso", "Por essas razões",
]
RESULT_PATTERNS = {
    "procedente": ["julgo procedente o pedido",
                   "acolho os pedidos formulados",
                   "reconheço a procedência da pretensão"],
    "improcedente": ["julgo improcedentes os pedidos",
                     "rejeito a pretensão inicial"],
    "appeal_denied": ["nego provimento ao recurso",
                      "conheço do recurso e lhe nego provimento"],
}
```

Mutações pós-render (perfil `noise_profile`): caixa alta; ausência de
acentos; espaços duplicados; hífens estranhos; quebras de página; cabeçalhos
no meio do texto; numeração automática; caracteres Unicode trocados; OCR
moderado; pontuação inconsistente; nomes de seção com e sem dois-pontos.
As mutações devem **recalcular/preservar offsets** — validador obrigatório.

## 6. Separação rigorosa entre gold e sintético

```text
data/segmenter_splits/      # somente gold real (inalterado)
data/segmenter_synthetic/   # documentos gerados
```

Proveniência explícita em cada registro:

```json
{
  "text": "...",
  "label": [...],
  "info": {
    "id": "synthetic_acordao_000042",
    "doc_type": "acordao",
    "synthetic": true,
    "generator_version": "v1",
    "template_family": "tjro_modern_ementa",
    "seed": 482901,
    "difficulty": "adversarial"
  }
}
```

Regras não negociáveis:

1. **Os gates G1–G5 continuam contando somente documentos reais.** O seed de
   20 docs ainda precisa escalar em volume, tribunais e suporte de classes
   raras — sintético não compra passagem pelos gates.
2. **Sintético jamais entra em validação ou teste:**
   `train = real + synthetic; validation = real only; test = real only,
   verified`. Caso contrário mede-se a capacidade do modelo de reconhecer o
   estilo do próprio gerador.
3. **Sem ciclo recursivo:** o segmentador não gera nem seleciona os dados de
   treino da própria próxima versão. Treinar recursivamente em sintético
   apaga as caudas da distribuição real.
4. O manifest separa as contagens:

```json
{
  "real_documents": 150,
  "synthetic_documents": 500,
  "real_support_by_class": {},
  "synthetic_support_by_class": {}
}
```

## 7. Protocolo experimental

Runs comparáveis (val/test sempre reais, nunca sintético/augmented):

| Run | Treino | Val/test |
|---|---|---|
| A | gold real | real |
| E | real + augmented (case/whitespace, §4-bis.4) | real |
| B | real + sintético simples | real |
| C | real + sintético adversarial | real |
| D | real + sintético balanceando classes raras | real |

Run E é o experimento de menor custo (fase 0, §8) e roda antes dos demais —
se o aumento por regex já não ajudar sobre A, é sinal de alerta antes de
investir na geração completa.

Métricas de comparação: macro-F1; macro-F1 sem classes fáceis; F1 por
classe; erros em `resultado`; confusão `voto_*` × `acordao_decisorio_*`;
falsos positivos em âncoras citadas; desempenho por tribunal e tipo
documental.

**Critério de aceitação: o sintético só é mantido quando melhora o teste
real.** "Parece plausível" não é critério. (A infraestrutura de comparação
entre runs já existe — W&B em `causaganha-segmenter`, com config/lineage por
run, do PR #792.)

## 8. Escopo da primeira implementação

Um PR pequeno adicionaria:

```text
scripts/generate_synthetic_segmenter.py
scripts/synthetic_segmenter/
    specs.py          # DocumentSpec + amostragem com seed
    renderer.py       # inserção de âncoras + registro de offsets
    phrase_banks.py   # variações de superfície por categoria + sinônimos curados
    corpus_stats.py   # estatísticas da distribuição real (dos textos.parquet)
    offset_shift.py   # utilitário de deslocamento de offset após mutação de comprimento
    mutations.py      # perfis de ruído sintético (§5.2) — usa offset_shift.py
    augment_real.py   # aumento por regex de gold real (§4-bis.4) — usa offset_shift.py
    validators.py     # invariantes + offsets + scrub de âncoras em texto real
    llm_content.py    # fase 2: conteúdo interno via LiteLLM (specs.py define, não rotula)
    llm_judge.py      # fase 2: juiz sintético-vs-real via LiteLLM (§4-bis.2/.3)
tests/test_synthetic_segmenter.py
```

**Fase 0 (mais barata, sem LLM, direto no gold existente):**
`offset_shift.py` + `augment_real.py` (§4-bis.4) — capitalização e
espaçamento nos 20 documentos gold já anotados. Não precisa de
`DocumentSpec`/renderer/geração nenhuma; é o menor experimento possível do
protocolo §7 (uma linha nova na tabela: Run E — `real + augmented
(case/whitespace)`, val/test real) e valida o utilitário de shift de offset
que a fase 1 também reutiliza. Sinônimo (a parte mais arriscada de §4-bis.4)
fica para depois de `phrase_banks.py` existir, pois depende da lista
curada.

**Fase 1 — geração estrutural completa, ainda sem LLM.** Um gerador
gramatical com phrase banks já valida: formato JSONL; offsets; cobertura
das 25 classes; invariantes da ontologia (um `dispositivo_abertura`
operativo, `resultado` só no verbo operativo, pareamento `_inicio`/`_fim`);
documentos sentença/acórdão; hard negatives; reprodutibilidade por seed. A
validação mecânica reutiliza `scripts/opf_annotate.py validate`.
`corpus_stats.py` (§4-bis.1) entra aqui — é leitura de parquet + contagem,
sem LLM — para que os phrase banks e as frequências do `DocumentSpec`
nasçam calibrados no corpus real em vez de "de cabeça".

A fase 2 introduz (a) conteúdo de LLM dentro das seções e (b) o juiz LLM
sintético-vs-real (§4-bis.2), mantendo âncoras e labels sob controle
determinístico do renderer (e, se executada por agente, via subagentes
conforme a skill `llm-work-via-subagents`, não script de API).

## 9. Recomendação concreta

Implementar primeiro o **gerador estrutural adversarial** (fase 1, sem LLM)
e usá-lo para aumentar principalmente `preliminar_*`, `custas_*`,
`honorarios_*`, `voto_*` e `acordao_decisorio_*` — as classes onde a
escassez estrutural é mais danosa — sem permitir que exemplos sintéticos
contem como gold real, e só promovendo o sintético que comprovadamente
melhora o teste real (§7).

## 10. Questões em aberto

1. **Volume alvo por classe rara** — quantos exemplos sintéticos por classe
   antes de saturar? (O experimento §7-D informa isso empiricamente.)
2. **Curriculum** — misturar sintético desde a época 1 ou introduzir após
   convergência inicial no real?
3. **Peso amostral** — sintético com peso menor que real no treino?
4. **Fase 2 (LLM)** — qual modelo/custo para o conteúdo interno, e como
   auditar que o conteúdo gerado não vazou âncoras fora do controle do
   renderer? (O validador §8 mitiga, mas a auditoria precisa ser definida.)
5. **Estilos de outros tribunais** — as `template_family` devem antecipar
   STJ/outros TJs já na fase 1 ou esperar gold real desses tribunais?
6. **Amostragem dos parquets para `corpus_stats`** — estratificada por
   tribunal/período (como o opf-finetune manda para anotação) ou o corpus
   TJRO disponível basta para calibrar a v1?
7. **Custo/limiar do juiz LLM** — julgar todo documento gerado ou uma
   amostra por `template_family`? Qual score mínimo por dimensão descarta
   um documento antes do treino?
8. **PII em conteúdo real reaproveitado** — a variante "conteúdo real,
   estrutura sintética" (§4-bis.1) herda texto público do DJEN; confirmar
   que a política de GOVERNANCE.md cobre a redistribuição desses trechos
   dentro de um dataset de treino sintético, ou se é preciso anonimizar
   partes antes.
9. **Recurso de sinônimos jurídicos (§4-bis.4)** — curar manualmente uma
   lista pequena e de alta precisão (ponto de partida: extrair as próprias
   variantes já usadas em `phrase_banks.py`, §5.2) ou usar um LLM para
   propor candidatos com revisão humana antes de entrar na lista? Um
   tesauro genérico de PT-BR é explicitamente rejeitado (§4-bis.4) pelo
   risco de trocar termos que parecem sinônimos mas não são
   intercambiáveis em contexto jurídico.
10. **Escopo do `offset_shift.py`** — construir um utilitário genérico de
    "aplicar N mutações e recalcular todos os spans" (mais reusável, mais
    complexo) ou funções específicas por tipo de mutação (mais simples,
    mais fácil de auditar cada caso)? Afeta tanto §4-bis.4 quanto o
    `mutations.py` sintético (§5.2).
