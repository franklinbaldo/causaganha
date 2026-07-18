# Annotation Guideline Changelog

Revision history for `annotation_guideline_v7.md`. Kept out of the guideline
itself so an annotator (LLM or human) reading it fresh gets only the current
rules, not the narrative of how they got that way — this file is for anyone
tracing *why* a rule reads the way it does, not for annotation-time reading.

Every entry here is a guideline-only change per RFC 0012 §5 point 1's last
bullet: none invalidate prior annotations, none bump `ontology_version`.

## v7.1 (RFC 0012 §9)

Fixed three gaps a single-document pilot found (see the RFC's PR history for
the pilot transcript):

- **Header phrase ordering** — the guideline said to tag literally "PODER
  JUDICIÁRIO" as `cabecalho_inicio`; real documents sometimes lead with
  "TRIBUNAL DE JUSTIÇA..." instead, in either order depending on source. Fix:
  tag whichever institutional phrase starts the header block first.
- **`relatorio`/`capitulo_merito` gaps** — a waiver clause ("Relatório
  dispensado na forma do art. 38...") explains why there's no report, it
  doesn't close one; it isn't a `relatorio_fim` closing cue. Many documents
  (short Juizados Especiais decisions especially) have no `capitulo_merito`
  heading at all — zero instances is a valid outcome, not an error.
- **`ref_processual` scope** — the model had tagged a generic internal
  attachment ID ("ID 66115008") as if it were a case number. Fix: must be
  CNJ-format or a genuine `fls.` folio pointer, not a generic internal ID.

A second pilot on the same document, run against this revision, confirmed
convergence on all three and also caught an unrelated production-technique
failure: text duplication instead of in-place wrapping (the model typed a
phrase once plain, then typed it again inside a tag, instead of wrapping the
occurrence it had already produced). Rule 6 was extended in response with an
explicit "wrap in place, never retype" instruction. A verbatim mismatch is a
risk signal that routes a record to independent review (RFC 0012 §9), not an
automatic rejection — it isn't a rigid release invariant.

## v7.2 (RFC 0012 §5 point 7)

The first real batch (5 documents beyond the pilot) showed the
"single-anchor = at most one per document" mechanical default doesn't fit
every single-anchor category. `dispositivo_abertura`, `resultado`, and
`ref_processual` are genuinely singular — they each name one fact about the
decision as a whole (the operative holding; which case this text belongs
to, for record-linking). `fundamentacao_legal` and `valor_condenacao` are
not: a real decision routinely cites the law more than once for different
points, and can state more than one genuinely different amount (moral vs.
material damages, an original vs. a corrected figure). Deduplicating those
down to "first occurrence" — which both ingestion scripts did at the time —
silently dropped real signal; a document citing art. 38 for the relatório
waiver and art. 55 for custas/honorários has two distinct
`fundamentacao_legal` spans, not one.

`ALLOW_MULTIPLE_SINGLE_ANCHOR` in `segmenter_dataset/ontology.py` now names
the two categories exempted from the one-per-document mechanical check;
every `validate_record` call site passes it.

Also narrowed `ref_processual`'s v7.1 fix: the guideline now says "this
document's own docket only," justified by the record-linking use case, not
merely "avoid generic internal IDs" (which is a real but separate criterion,
kept alongside it).

## v7.3 (production technique only — Rule 6, no ontology or category
semantics change)

A flat `<relatorio_inicio>`/`<relatorio_fim>` pair is two unrelated tag
names that happen to share a prefix; XML already has a native way to say
"these two things bound one region" — nesting. Start/end pairs are now
produced as one `<base>` wrapper element (named after the category, e.g.
`relatorio`) with generic `<inicio>`/`<fim>` children reused across every
pair category, instead of inventing a distinct flat tag name per role.
Anything else that textually falls inside the region — another category's
anchor, like `ref_processual` sitting inside a document's `cabecalho` —
nests inside the wrapper too. Single-anchor categories are unaffected;
there's no region to express, so they stay flat leaf tags exactly as
before.

Matches `segmenter_dataset/store.py`'s corresponding writer/reader rewrite
(RFC 0012 §8) — reading is fully backward compatible with the pre-v7.3 flat
format, so annotations produced under v7.1/v7.2 didn't need re-annotation,
only the on-disk corpus was regenerated (same content, new serialization).
