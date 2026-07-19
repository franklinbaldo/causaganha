# Technique 1 annotation prompt (canonical)

The prompt to use, verbatim (only the two `{...}` placeholders filled in),
whenever spawning one subagent per document for Technique 1 — real-document
LLM annotation (RFC 0012 §8/§9). Improvising this prompt per call is what
produced batch1's ~45% failure rate; use this template instead so results
are comparable across documents and across sessions, and so prompt fixes
get made in one place instead of re-invented ad hoc each time.

## Why it's shaped this way

Batch1 (RFC 0012 §9's changelog) found 8 of 20 subagents produced **zero
tags** despite being told exactly what to do. Reading the actual
transcripts (not just final output) showed a consistent shape: read
guideline, read document, brief thinking, jump straight to a final answer
that just echoes the source — no tags. One subagent even caught the gap
mid-generation ("Wait, I need to re-output this with the actual XML tags
inserted") and then pasted the identical untagged text again anyway.

The common thread: the task was structured as one uninterrupted generation
with no forced checkpoint between "read the document" and "commit to a
final answer." This template adds two checkpoints — enumerate expected
categories *before* tagging, verify the draft *after* — inside the same
turn, so a subagent that would otherwise silently skip the tagging work
has to notice it did.

## The prompt

```
You're producing ONE independent annotation for a Brazilian judicial-decision
span-labeling dataset (OPF BIOES token classification). This is real
production annotation work (Technique 1, RFC 0012 §8/§9), not a test.

Do this in explicit, separate steps. Do not skip ahead to the final answer.

1. Read the annotation guideline at
   `data/segmenter_splits/annotation_guideline_v7.md` (current rules only —
   you don't need the sibling CHANGELOG to annotate).
2. Read the document at `{document_path}`. {document_type_hint}
3. Before writing any tags, list which categories from BOTH anchor schemes
   (the single-anchor table, the start/end pairs table) you can actually
   find in this document, and roughly whereabouts. A short sentença
   typically has 5-12 anchors total; a longer acórdão more. If your list
   has fewer than ~5 entries for a document longer than a page, re-read
   the document before continuing — you are very likely under-reading it,
   not looking at a genuinely sparse one.
4. Produce the tagged reproduction: the ENTIRE document text verbatim,
   character-for-character, with inline XML tags per the guideline's
   Rule 6 — single-anchor categories get one flat tag; start/end pairs
   nest under a wrapper element with generic `<inicio>`/`<fim>` children
   (see the guideline for the exact shape and a worked example).
5. Before finalizing, check your own draft:
   - Does every category from your step 3 list actually appear as a tag?
     If you dropped one, go back and add it — don't finalize without it.
   - Mentally strip every tag from your draft and compare what's left to
     the document text from step 2, character for character. They must be
     IDENTICAL. If they differ, you've duplicated or altered text
     somewhere — find the mismatch and fix it by wrapping the existing
     occurrence in place. Never fix it by retyping the phrase again.
   - Zero tags is only a valid outcome for an unusually short or malformed
     document — if that's genuinely the case here, say so explicitly
     instead of silently returning the plain, untagged text.

Output ONLY the fully tagged document text as your final answer — no
preamble, no explanation, no markdown code fences. Steps 1-3 and 5 are
your own working process; only step 4's verified result belongs in your
answer.
```

## Filling the placeholders

- `{document_path}` — absolute path to the plain-text source document.
- `{document_type_hint}` — one line steering category expectations, e.g.:
  - `This is a SENTENÇA (single-judge first-instance decision). No voto/acordao_decisorio categories should appear.`
  - `This is an ACÓRDÃO (collegiate decision). voto and acordao_decisorio may appear alongside the sentença-style categories.`

## After the batch

Verify every returned annotation programmatically before trusting it —
this prompt reduces the failure rate, it doesn't eliminate the need for
the checks `scripts/ingest_juris_technique1_batch.py` already runs
(verbatim-fidelity reconstruction, mechanical validation). A subagent's own
self-check is a cheap first filter, not a substitute for the real one.
