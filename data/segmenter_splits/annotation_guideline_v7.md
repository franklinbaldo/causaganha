# Annotation Guideline — CausaGanha Decision Segmenter v7

## Overview

Label short anchor spans in Brazilian judicial decisions. OPF uses BIOES
token classification with ~257-token banded attention. Portuguese is OOD
for the English-primary base model — short, distinctive cues work best.

## Two anchor schemes

### Single-anchor (6 categories)

Mark the **opening cue** only (a few words). The region extends from this
anchor to the next anchor or end of document. Never label a long region
as one span.

| Category | What to mark | Example surface |
|---|---|---|
| `dispositivo_abertura` | The formulaic opening of the operative part | "Ante o exposto" / "Pelo exposto" / "Posto isso" |
| `resultado` | The operative verb phrase | "julgo procedente" / "nego provimento" / "extingo o feito" |
| `ref_processual` | Case number (CNJ format) or folio reference | "1234567-89.0123.4.56.7890" / "fls. 42" |
| `valor_condenacao` | Monetary amount in a condemnation | "R$ 5.000,00" |
| `ref_normativa` | Citation of statute, article, or precedent | "art. 927 do CPC" / "Súmula 331 do TST" |
| `fundamentacao_legal` | Legal reasoning phrase citing authority | "nos termos do art. 932 do CPC" |

### Start/end pairs (10 region types, 20 categories)

Mark a short **opening cue** as `_inicio` and a short **closing cue** as
`_fim`. The region is everything between them (inclusive). If no closing
cue exists, the `_inicio` extends to EOD (reconstructed as unmatched).

| Base | `_inicio` example | `_fim` example |
|---|---|---|
| `cabecalho` | "PODER JUDICIÁRIO" / court name | Last party/OAB before SENTENÇA |
| `ementa` | "EMENTA:" | Last line before RELATÓRIO |
| `relatorio` | "RELATÓRIO:" / "Trata-se de" | "É o relatório." |
| `capitulo_merito` | "DO MÉRITO:" / "DECIDO" / "Mérito:" | "DISPOSITIVO" / start of dispositivo |
| `preliminar` | "DAS PRELIMINARES" / "PRELIMINAR" | End of preliminary analysis |
| `honorarios` | "HONORÁRIOS:" / "Dos honorários" / "Sem honorários" | End of fee determination |
| `custas` | "CUSTAS:" / "Das custas" / "Sem custas" | End of costs determination |
| `encerramento` | "Publique-se." / "P.R.I." | Judge title at end of document |
| `voto` | "VOTO" / "É como voto" (start of a judge's reasoning in an acórdão) | "É o voto." / last line before the next vote or the decisório |
| `acordao_decisorio` | "ACORDAM os Desembargadores" / "Vistos, relatados e discutidos" | "à unanimidade" / "por maioria" + close of the collegiate result |

**Acórdão (second-instance) notes.** `voto` and `acordao_decisorio` only
appear in collegiate decisions (Câmaras, Turmas Recursais). An acórdão's
operative result is the **collegiate** `acordao_decisorio` ("ACORDAM ...");
do **not** also tag a single-judge `dispositivo_abertura` inside an
individual `voto` as the decision's operative opening. In a sentença
(first instance) these two categories do not occur.

## Rules

1. **Anchor spans are short** — typically 1-5 words, never more than
   ~120 characters. If you're selecting a full paragraph, stop.
2. **One dispositivo_abertura per decision.** A document may contain
   multiple "Ante o exposto" but only the operative one gets labeled.
3. **resultado only on the operative verb**, not on reasoning verbs,
   "Decido", intermediate rulings, or quoted precedent outcomes.
4. **Trim whitespace** — span boundaries must not include leading or
   trailing spaces.
5. **No overlapping spans** — OPF BIOES assigns one label per token.
6. **Character offsets** — `text[start:end]` must equal the span surface.
   Offsets are Python string indices (UTF-8 codepoints), end-exclusive.

## Anti-patterns

- Labeling "Decido" as `dispositivo_abertura` — this is an interlocutory
  verb, not the dispositivo opening.
- Labeling reasoning paragraphs as `resultado` — resultado is only the
  operative holding.
- Labeling every article citation as both `ref_normativa` and
  `fundamentacao_legal` — pick the more specific one; don't overlap.
- Very long `ementa_inicio`...`ementa_fim` spans covering hundreds of
  words — mark just the opening/closing cues; reconstruction handles
  the region between them.
