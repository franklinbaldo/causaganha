# Benchmark Design — Dimensions, Targets, and Oracle

This note states the *theory* behind the gold benchmark: what we measure, why,
and how the gold labels are produced. It is the rationale companion to
`README.md` (which documents the concrete schema fields).

## 1. The label space is orthogonal, not flat

Brazilian procedural doctrine keeps three things separate that a flat
`outcome` enum collapses into one:

| Axis | Doctrinal basis | Examples |
| :--- | :--- | :--- |
| **(a) Juízo** — admissibility vs. merits | CPC art. 485 (sem mérito) vs. art. 487 (com mérito) | `extinto sem mérito` is a *terminação*, not a peer of `procedente` |
| **(b) Resultado quanto ao pedido** — the *invariant* substantive winner | who actually prevailed on the claim | stable across instances |
| **(c) Disposição do recurso** — instance-local appeal result | juízo de admissibilidade (`não conhecido`) + provimento (`provido`/`não provido`) | `provido` ≠ "plaintiff won" by itself |

The crux for appeals: `procedente`/`improcedente` describe the fate of the
**pedido** (the claim); `provido`/`não provido`/`não conhecido`/`prejudicado`
describe the fate of the **recurso** — a *different object*. Because of the
**efeito substitutivo** (CPC art. 1.008), a recurso *conhecido e provido*
replaces the lower decision, so the surface word alone does not tell you who
won the dispute. You need `recorrente_polo` (who appealed) to recover it.

## 2. The benchmark target is the invariant winner, not the surface word

A first-instance `procedente` and an appellate `recurso do réu não provido`
describe the **same substantive event**: the plaintiff prevailed. Scoring the
surface label treats them as different, injecting label noise *by design* that
caps achievable accuracy regardless of model quality (a construct-validity
failure — we'd be measuring procedural vocabulary, not who won).

The invariant target is the **winning polo**:

```
WinnerPolo = A (autor / plaintiff) | P (passivo / defendant) | draw | unknown
```

The mapping `(outcome, recorrente_polo) → WinnerPolo` is owned by
`recurso_resolver.resolve_winner_polo` and carries the polarity inversion:

```
provido     + recorrente='A' → A      não provido + recorrente='A' → P
provido     + recorrente='P' → P      não provido + recorrente='P' → A
```

`benchmark_metrics.to_winner_polo` is the single benchmark entry point over it.

## 3. Evaluation = gate + conditional (selective prediction)

~40% of sampled communications are interlocutórias / despachos — *não-decisões
de mérito* that legitimately have no winner. They do not belong in an outcome
metric; mixing them produces a single accuracy number that means nothing.

We decompose into two independent tasks:

- **Gate** — "is this a ratable merits decision?" Binary `ratable`
  (polo ∈ {A, P, draw}) vs. `not_ratable` (unknown). Interlocutórias, despachos,
  `extinto sem mérito`, and inadmissible appeals (`não conhecido`/`prejudicado`)
  resolve here.
- **Conditional** — "given a ratable decision, which polo won?" Scored **only**
  over gold-ratable cases, so the procedural `unknown` mass can neither mask nor
  flatter outcome performance.

A flat number hides this; e.g. on the current TJRO sample the flat surface score
is misleadingly low while the decomposition shows a strong gate (~87%) and a
solid conditional (~76%) bottlenecked by rare-class support, not by the model.

Always report **per-class support** — per-polo F1 over 7 cases has a confidence
interval too wide to act on. Sampling must be **stratified** by
`fase_processual × decision_type × outcome` with a minimum support per stratum,
especially for the recursal cases that exercise the polarity inversion.

## 4. The gold oracle: independent, capable, agreement-measured — not human

Measurement theory requires the oracle to be **(1) independent of the system
under test, (2) at least as capable as it, and (3) of *measurable*
reliability.** None of these require a human annotator — they require a
*reliable independent judge*. A panel of capable 2026 frontier LLMs satisfies
all three, and its reliability is quantified exactly as a human panel's would
be: inter-annotator agreement across models (Cohen's κ / Krippendorff's α).

The real failure mode to avoid is **circularity**: labeling the gold with the
*same* model (or config) that powers the production classifier measures
self-agreement, not accuracy. The safeguards:

- **Capability/independence gap (teacher > student).** The gold oracle runs a
  *stronger or differently-configured* setup than the production classifier —
  full-text, higher reasoning budget, and a **multi-model panel**, distinct from
  the cheap/fast production path under test.
- **Consensus + measured agreement.** Treat multi-model consensus as the gold
  label and report cross-model κ/α as the reliability of the benchmark itself.
  Low agreement on a case flags it for review or exclusion, not silent
  inclusion.
- **No self-evaluation.** A classifier (or its embedding/LLM backbone) must not
  be scored against gold labels its own model produced.

`is_human_verified` therefore marks an *optional stronger anchor*, not a
prerequisite for validity — the benchmark is a measured LLM-panel gold standard,
not a human-labeled one.

## 5. Consequences

- New outcome vocabulary (e.g. the recursal axis) is a **schema version bump**
  (see `README.md`), and is only benchmarkable once the analyzer that emits it
  exists and a stratified recursal sample is labeled by the panel oracle.
- Scoring code lives in `causaganha.analysis.benchmark_metrics`
  (`evaluate_invariant`); the runner is `scripts/evaluate_heuristics.py`.
- Surface-label accuracy is retained as a **secondary diagnostic** only; the
  invariant gate + conditional is the primary signal.
