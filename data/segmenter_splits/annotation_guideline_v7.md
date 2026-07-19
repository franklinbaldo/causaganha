# Annotation Guideline — CausaGanha Decision Segmenter v7.3

Revision history: see `annotation_guideline_v7_CHANGELOG.md`. This file is
the current rules only.

## Overview

Label short anchor spans in Brazilian judicial decisions. OPF uses BIOES
token classification with ~257-token banded attention. Portuguese is OOD
for the English-primary base model — short, distinctive cues work best.

## Two anchor schemes

### Single-anchor (6 categories)

Mark the **opening cue** only (a few words). The region extends from this
anchor to the next anchor or end of document. Never label a long region
as one span.

Most single-anchor categories name one fact about the decision as a whole
and take **at most one tag per document** — `dispositivo_abertura` and
`resultado` because only the *operative* mention counts (Rules 2-3),
`ref_processual` because its job is linking this text to exactly one case
(a multi-valued link is useless). `fundamentacao_legal` and
`valor_condenacao` are different: tag **every** distinct occurrence, not
just the first. See each row below for specifics.

| Category | What to mark | Example surface |
|---|---|---|
| `dispositivo_abertura` | The formulaic opening of the operative part | "Ante o exposto" / "Pelo exposto" / "Posto isso" |
| `resultado` | The operative verb phrase | "julgo procedente" / "nego provimento" / "extingo o feito" |
| `ref_processual` | **This document's own docket only** — the case number (CNJ format) or "fls." folio reference identifying the decision being read, for record-linking. Not a generic internal system/attachment ID ("ID 66115008") even when it looks superficially similar; if in doubt whether a number is CNJ-format or a folio pointer, don't tag it. **Leave every *other* case's number untagged** — a prior conviction, a cited precedent's process number — even if it's genuinely CNJ-format; that's expected, not an omission, since this category exists to identify *this* document's case, not to catalog every case number it mentions | "1234567-89.0123.4.56.7890" / "fls. 42" |
| `valor_condenacao` | Monetary amount in a condemnation — **tag every genuinely distinct amount.** A document with moral damages of R$5.000,00 *and* material damages of R$2.000,00 has two spans, not one; if the same figure is simply restated in a later clause, tag that occurrence too — repeats aren't an error here | "R$ 5.000,00" |
| `ref_normativa` | Citation of statute, article, or precedent | "art. 927 do CPC" / "Súmula 331 do TST" |
| `fundamentacao_legal` | Legal reasoning phrase citing authority — **tag every distinct citation**, not just the first. A decision citing art. 38 to waive the relatório and art. 55 for custas/honorários has two spans | "nos termos do art. 932 do CPC" |

### Start/end pairs (10 region types, 20 categories)

Mark a short **opening cue** as `_inicio` and a short **closing cue** as
`_fim`. The region is everything between them (inclusive). If no closing
cue exists, the `_inicio` extends to EOD (reconstructed as unmatched).

| Base | `_inicio` example | `_fim` example |
|---|---|---|
| `cabecalho` | Whichever institutional phrase starts the header block first — "TRIBUNAL DE JUSTIÇA..." and "PODER JUDICIÁRIO" both appear, in either order depending on source; tag the one that comes first in this document, not literally the string "PODER JUDICIÁRIO" | Last party/OAB before SENTENÇA |
| `ementa` | "EMENTA:" | Last line before RELATÓRIO |
| `relatorio` | The "Relatório"/"RELATÓRIO:" heading when one is present, even if immediately followed by a waiver clause ("dispensado na forma do art. 38..."); if genuinely no heading word appears, "Trata-se de" | "É o relatório." A waiver clause is not a closing cue — "Relatório dispensado na forma do art. 38..." explains *why* there's no report, it doesn't close one — tag it as `fundamentacao_legal` (it cites a statute) if it qualifies, not `relatorio_fim`. Leave `relatorio_fim` unmatched (declared reason: "relatório dispensado, sem cue de fechamento") when no real closing phrase exists |
| `capitulo_merito` | "DO MÉRITO:" / "DECIDO" / "Mérito:" — many documents (short Juizados Especiais decisions especially) have no such heading at all. That's expected, not an error — don't force a `capitulo_merito` tag onto plain reasoning prose. Zero instances of a category in a document is a valid outcome; `relatorio`'s implicit region simply extends to `dispositivo_abertura` instead | "DISPOSITIVO" / start of dispositivo |
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
6. **Production technique: reproduce, don't compute offsets.**
   Reproduce the ENTIRE document text verbatim — character-for-character,
   no corrections, no normalization — inserting inline XML tags around
   each anchor span. Never report `start`/`end` as integers; they're
   derived afterward, mechanically, from where the tags land (RFC 0012
   §8) — position arithmetic is a known LLM failure mode this sidesteps
   entirely. A tag's content must still satisfy every rule above (short,
   trimmed, no overlap) — it's the same span, just placed inline instead
   of reported as offsets.

   **Single-anchor categories** (the 6-category table) get one flat tag
   named after the category:
   `<ref_processual>7059080-46.2021.8.22.0001</ref_processual>`.

   **Start/end pairs nest, using XML's own open/close structure — don't
   invent a separate tag name per role.** Wrap the whole region in one
   element named after the category base, with generic `<inicio>` and
   `<fim>` children (reused across every pair category — never
   `<cabecalho_inicio>`):

   ```xml
   <cabecalho><inicio>PODER JUDICIÁRIO</inicio> Comarca de Porto Velho,
   Processo 7059080-46.2021.8.22.0001, REQUERENTE: ... <fim>REQUERIDO SEM
   ADVOGADO(S)</fim></cabecalho>
   ```

   The interior prose between the two anchors stays exactly as it was —
   don't tag it, don't touch it — it's just inside `<cabecalho>` by virtue
   of sitting between `<inicio>` and `<fim>`. If another category's anchor
   falls in that interior text (e.g. a `ref_processual` case number
   printed inside the header block), tag it normally, in place — it ends
   up nested inside `<cabecalho>` too, which is correct, not an error.
   **Unmatched pair** (no closing cue in this document): still wrap, just
   with one child — `<relatorio><inicio>Relatório</inicio></relatorio>` —
   don't fabricate a closing tag and don't leave the wrapper off.

   **Wrap the existing text in place — never retype or duplicate it.**
   Typing a phrase once plain and then typing it *again* inside a tag,
   instead of wrapping the occurrence you already produced, gives valid
   XML that is no longer a verbatim reconstruction of the source — a
   silent corruption. If you notice you already emitted a phrase
   untagged, go back and add the tag around it — don't emit it a second
   time.

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
