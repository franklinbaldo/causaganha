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

Quatro runs comparáveis (val/test sempre reais):

| Run | Treino | Val/test |
|---|---|---|
| A | gold real | real |
| B | real + sintético simples | real |
| C | real + sintético adversarial | real |
| D | real + sintético balanceando classes raras | real |

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
    phrase_banks.py   # variações de superfície por categoria
    corpus_stats.py   # estatísticas da distribuição real (dos textos.parquet)
    mutations.py      # perfis de ruído, preservando offsets
    validators.py     # invariantes + offsets + scrub de âncoras em texto real
tests/test_synthetic_segmenter.py
```

A primeira versão **não chama LLM**. Um gerador gramatical com phrase banks
já valida: formato JSONL; offsets; cobertura das 25 classes; invariantes da
ontologia (um `dispositivo_abertura` operativo, `resultado` só no verbo
operativo, pareamento `_inicio`/`_fim`); documentos sentença/acórdão; hard
negatives; reprodutibilidade por seed. A validação mecânica reutiliza
`scripts/opf_annotate.py validate`. `corpus_stats.py` (§4-bis.1) já entra na
fase 1 — é leitura de parquet + contagem, sem LLM — para que os phrase banks
e as frequências do `DocumentSpec` nasçam calibrados no corpus real em vez
de "de cabeça".

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
