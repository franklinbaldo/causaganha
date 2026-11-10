# AGENTS.md — Autonomous Agent Operating Manual for CausaGanha

This document provides operational guidelines, system architecture, invariants, and best practices for autonomous AI coding agents (Antigravity, Codex, Claude Code, etc.) operating in the **CausaGanha** repository.

---

## 1. System Overview & Repository Domains

CausaGanha operates two interconnected runtime domains for Brazilian judicial data:

1. **DJEN Backup & Archival Engine (`src/djen_backup`)**:
   - High-throughput asynchronous pipeline synchronizing daily court gazettes from the Diário de Justiça Eletrônico Nacional (DJEN) to the Internet Archive (IA).
   - Event-driven manifest architecture (`sync-manifest.parquet`).
2. **Jurimetrics & Decision Analysis Pipeline (`src/causaganha`)**:
   - 100% offline, zero-cost NLP and ML pipeline segmenting full-text decisions, extracting legal entities (parties, OABs, judges), and classifying judgment outcomes according to the Brazilian Code of Civil Procedure (CPC/2015).
   - Active learning flywheel with anomaly detection and automated ratchet regression gates.
3. **Public Web Dashboard (`web/`)**:
   - Astro 7 + Svelte 5 frontend with Panda CSS, providing interactive public dashboards and the Before-vs-After decision audit comparator (`/auditoria`).

---

## 2. Non-Negotiable Agent Invariants

Every agent modifying this repository **MUST** adhere to the following rules:

### 2.1. Environment & Execution
- **Always use `uv run`**: Never execute bare `python`, `pip`, or `pytest`. Use `uv run python ...`, `uv run pytest -q`, `uv run ruff check`.
- **Zero External API Cost / 100% Offline CPU Inference**: All core decision extraction, segmentation, entity grounding, and active learning must execute locally on CPU using scikit-learn, regex, and statistical NLP. External paid LLM APIs must **never** be added to production inference paths.
- **Throughput & Latency Target**: Production pipelines must achieve **>= 40 documents/second** with **P50 latency <= 25 ms** per document on commodity CPU cores.

### 2.2. Model Ratchet Gate (Anti-Regression Invariant)
- Any retraining of the classification model or active learning iteration **MUST** pass through `ModelRatchetGate` (`src/causaganha/decisoes/model_ratchet.py`).
- A candidate model is rejected and discarded if its test ROC-AUC or macro-F1 score is lower than the production baseline (`BASELINE_ROC_AUC = 0.865`).

### 2.3. Legal Domain Fidelity (CPC/2015 & DataJud)
- **Do not reduce judgments to naive binary "win/loss"**: Brazilian judicial outcomes are multi-dimensional. Distinguish admissibility from merit (CPC art. 485 vs. 487).
- **Honor Appellate Polarity Inversion (CPC art. 1.008)**: Second-instance judgments (*acórdãos*) judge the appeal (*recurso*), not the initial claim. A decision granting the defendant's appeal (*recurso do réu provido*) represents a victory for the defense. Always route appellate outcomes through `recurso_resolver.py`.
- **Validate CNJ Numbers with Módulo 97**: All process numbers must pass the official CNJ checksum algorithm (`validate_cnj_checksum`).

### 2.4. Web Security & Content-Security-Policy (CSP)
- Every web page in `web/public/` or `web/src/pages/` must comply with strict CSP policies.
- The build pipeline enforces `web/scripts/injectCspHashes.mjs`. Static HTML pages must include:
  ```html
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';">
  ```
  Missing CSP tags will fail the CI build.

### 2.5. JSON Serialization Invariant (No `NaN` in JSON for Web)
- When exporting JSON datasets for browser consumption (such as `web/public/visualizer_data.json` via `scripts/export_visualizer_data.py`), always replace Pandas/NumPy `np.nan` with Python `None` (which renders as `null`).
- Always pass `allow_nan=False` to `json.dump()` or `json.dumps()`. Python's default behavior emits unquoted `NaN` / `Infinity`, which violates ECMA-404 / RFC 8259 and crashes browser `JSON.parse()`.

### 2.6. Code Quality & Exception Handling
- **No blind `except Exception`**: Use specific exception types (`httpx.HTTPError`, `OSError`, `ValueError`). Bulkhead worker loops may catch `Exception` broadly only if `logger.exception(...)` records the full traceback, as documented in [ADR 0011](docs/adr/0011-broad-except-in-worker-loop-bulkheads.md).
- **Strict Typing**: Python 3.12+ syntax with `from __future__ import annotations` and PEP 604 pipe unions (`str | None`).
- **Formatting**: Must pass `uv run ruff check` and `uv run ruff format --check`.

---

## 3. Core AI & Jurimetrics Engine Architecture

```
[ Raw DJEN Text / Publication ]
               │
               ▼
┌───────────────────────────────────────────────────────────┐
│ 1. FullDocumentStructuralSegmenter                        │
│    Monotonic Viterbi / HMM Sequential State Machine       │
│    CABECALHO ➔ RELATORIO ➔ FUNDAMENTACAO ➔ DISPOSITIVO ➔  │
│    ENCERRAMENTO                                           │
└──────────────────────────────┬────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 2. Section-Aware NER        │ │ 3. Hybrid Dispositif        │
│    (CompositeEntityExtractor)│ │    Segmenter & Classifier   │
│ - CNJ Modulo 97 Validation  │ │ - Regex + RF Token Boundary │
│ - Parties: CABECALHO        │ │ - CPC 2015 Hierarchical     │
│ - OAB / Lawyers: CABECALHO  │ │   Dispositivo Outcome       │
│ - Judge Signatures:         │ │   (PROCEDENTE, PROVIDO...)  │
│   ENCERRAMENTO only         │ └──────────────┬──────────────┘
└─────────────────────────────┘                │
                                               ▼
                                ┌─────────────────────────────┐
                                │ 4. Appellate Polarity       │
                                │    Resolver                 │
                                │ - Recurso x Polo (A vs P)   │
                                │ - CPC art. 1.008 Inversion  │
                                │ - Substantive Success Rate  │
                                └─────────────────────────────┘
```

### 3.1. 5-Section Structural Segmentation
- **File**: `src/causaganha/decisoes/structural_segmenter.py`
- **Class**: `FullDocumentStructuralSegmenter`
- **Sections**:
  1. `CABECALHO`: Court identification, process number, party names, subject line.
  2. `RELATORIO`: Procedural history, claims, defenses.
  3. `FUNDAMENTACAO`: Legal merits, analysis, jurisprudence citation.
  4. `DISPOSITIVO`: Final adjudication command (`"DISPOSITIVO"`, `"POSTO ISSO"`, `"JULGO..."`).
  5. `ENCERRAMENTO`: Magistrate signature, date, location.
- **Decoding Mechanism**: Monotonic state machine with forward-only transitions. Once the segmenter enters `DISPOSITIVO`, it cannot revert to `RELATORIO` or `FUNDAMENTACAO`.

### 3.2. Hybrid Dispositivo Extraction & Outcome Classification
- **Files**: `src/causaganha/decisoes/hybrid_segmenter.py`, `src/causaganha/decisoes/dispositivo_classifier.py`
- **Classes**: `HybridDispositifSegmenter`, `DispositivoClassifier`
- **CPC Taxonomy Classes**:
  - `PROCEDENTE`: Full claim approval for claimant.
  - `PARCIALMENTE_PROCEDENTE`: Reciprocal outcome, partial relief.
  - `IMPROCEDENTE`: Rejection on merits (res judicata, CPC art. 487, I).
  - `EXTINTO_SEM_RESOLUCAO_MERITO`: Dismissal without merit (CPC art. 485).
  - `HOMOLOGACAO_ACORDO`: Judicial settlement approval (CPC art. 487, III, b).
  - `PROVIDO`: Appellate reversal in favor of appellant.
  - `IMPROVIDO`: Appellate confirmation of lower court judgment.
  - `PARCIALMENTE_PROVIDO`: Partial appellate relief.
  - `NAO_CONHECIDO`: Non-admissibility of appeal.

### 3.3. Multi-Algorithm Section-Aware NER
- **File**: `src/causaganha/decisoes/ner/composite.py`
- **Class**: `CompositeEntityExtractor`
- **Rules**:
  - **Módulo 97 CNJ**: Strict check-digit verification prevents false process numbers.
  - **Section Routing**: Magistrate names are extracted exclusively from the `ENCERRAMENTO` section to avoid misclassifying cited judges in `FUNDAMENTACAO`.
  - **Party Grounding**: Matches extracted entity spans against structured metadata fields (`polo_ativo`, `polo_passivo`).
  - **Lawyer & OAB Identification**: Detects OAB numbers (UF + digits) and associates them with their respective parties in `CABECALHO`.

### 3.4. Appellate Polarity Resolution (CPC art. 1.008)
- **File**: `src/causaganha/analysis/recurso_resolver.py`
- **Function**: `resolve_winner_polo(dispositivo_class, recorrente_polo)`
- **Output**: `WinnerPolo` (`"A"` = Author/Claimant, `"P"` = Defendant/Passivo, `"draw"` = Partial, `"unknown"`).
- **Logic**:
  - `PROVIDO` + Recorrente = Passivo (`P`) ➔ Winner = `P` (Defense victory).
  - `IMPROVIDO` + Recorrente = Passivo (`P`) ➔ Winner = `A` (Claimant victory confirmed).

---

## 4. Active Learning Flywheel & Retraining Loop

The active learning flywheel continuously improves model accuracy on real DJEN publications without manual labeling friction:

```
                  ┌───────────────────────────────┐
                  │ Ingest DJEN Parquet Batch     │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ Isolation Forest Anomaly Scan │
                  │ (Detect Outliers & Ambigua)   │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ THX-02 Heuristic Legal Audit  │
                  │ (Span Corrections & Labeling) │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ Active Learning Pool          │
                  │ data/audit/active_learning_   │
                  │ pool.jsonl                    │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ Train Candidate Model         │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │ ModelRatchetGate Verification │
                  │ (ROC-AUC >= Baseline?)        │
                  └──────┬─────────────────┬──────┘
                         │ Pass            │ Reject
                         ▼                 ▼
                  [ Promote to Prod ]   [ Keep Baseline ]
```

### 4.1. Key Scripts
- **Flywheel Runner**:
  ```bash
  uv run python scripts/run_flywheel_until_saturation.py \
    --dataset data/benchmark/djen_1000_sample.parquet \
    --max-iterations 3 \
    --sample-size 40
  ```
- **Active Learning Flywheel Core**:
  ```bash
  uv run python scripts/thx02_active_learning_flywheel.py --dataset data/benchmark/djen_1000_sample.parquet
  ```
- **1,000 Document DJEN Benchmark**:
  ```bash
  uv run python scripts/classify_djen_sample_1000.py
  ```
- **Visualizer Data Exporter**:
  ```bash
  uv run python scripts/export_visualizer_data.py
  ```

---

## 5. Web Visualizer & Public Audit Surface

The repository provides an interactive Before-vs-After comparison tool for auditing segmentation, extraction, and CPC classifications:
- **Public URL**: `https://franklinbaldo.github.io/causaganha/auditoria`
- **Standalone App**: `web/public/auditoria.html` (pure vanilla HTML/CSS/JS, zero NPM dependencies, full CSP support, dynamic base URL resolution for GitHub Pages subpath `/causaganha/`).
- **Data Source**: `web/public/visualizer_data.json` containing 58+ curated decisions generated by `scripts/export_visualizer_data.py`.

### 5.1. Visualizer UX Invariants & Features
1. **Immediate Zero-Click Presentation**:
   - On load, the page immediately displays a randomly selected decision (`window.addEventListener('DOMContentLoaded', () => navigateRandom())`). Users never see an empty screen or need to click to load the first item.
2. **Sequential & Random Stepper Navigation**:
   - Top and bottom control bars provide `◀ Anterior`, `Próxima ▶`, and `🎲 Sortear` buttons, along with full-width keyboard hotkeys (`ArrowLeft`, `ArrowRight`, `r` for random).
3. **Proportional 5-Section Segmentation Ribbon**:
   - Horizontal color-coded track displaying relative character percentages for `1. Cabeçalho` (blue), `2. Relatório` (amber), `3. Fundamentação` (purple), `4. Dispositivo` (emerald), and `5. Encerramento` (slate).
   - In the raw DJEN text ("Antes"), visual cut markers (`✂️ SEÇÃO 1: CABEÇALHO`, `🎯 SEÇÃO 4: DISPOSITIVO`, etc.) explicitly show where boundaries are partitioned.
4. **Dual JSON Payload Inspection & Export**:
   - **`{ } Ver JSON` Tab**: Top toggle switching between the visual comparison view and a syntax-highlighted, full-screen JSON payload viewer with live character counts and download action.
   - **In-Place JSON Accordion**: Collapsible drawer (`📦 Inspecionar Payload JSON desta Decisão`) at the bottom of the structured view for inspecting raw JSON without leaving the visual comparison.
   - **`📋 Copiar JSON` Button**: One-click clipboard copy with visual feedback toast.
   - **`⬇️ Baixar .json` Button**: Downloads individual decision as an indented `.json` file named after the court and process ID.

---

## 6. Skills & Jurimetrics References

Autonomous agents should refer to the following skill and documentation packages located in `.agents/`:

- **Skill Entry Point**: `.agents/skills/jurimetria/SKILL.md`
- **CPC Taxonomy Reference**: `.agents/skills/jurimetria/references/taxonomia_processual_cpc.md`
- **10-Point Audit Checklist**: `.agents/skills/jurimetria/references/auditoria_checklist.md`
- **Automated Compliance Auditor**:
  ```bash
  uv run python .agents/skills/jurimetria/scripts/audit_jurimetrics_compliance.py --input data/audit/classificacao_1000_djen.parquet
  ```

---

## 7. Developer & Agent Workflow

### 7.1. Running Quality Checks
Before committing any changes, run:
```bash
# 1. Linting and formatting
uv run ruff check
uv run ruff format --check

# 2. Pytest suite
uv run pytest -q tests/test_structural_segmenter.py tests/test_recurso_resolver.py tests/test_spike_thx02.py

# 3. Web build and CSP audit (if web/ was modified)
cd web && npm test && npm run build && cd ..
```

### 7.2. Git & PR Protocol
Because the `main` branch is protected by status checks:
1. Never push directly to `main`.
2. Create a feature branch: `git checkout -b <type>/<description>`.
3. Commit with Conventional Commits: `feat(...)`, `fix(...)`, `docs(...)`, `test(...)`.
4. Push and create a pull request:
   ```bash
   git push -u origin <branch-name>
   gh pr create --title "..." --body "..."
   ```
5. Merge with squash and delete branch:
   ```bash
   gh pr merge <pr-number> --squash --delete-branch --admin
   ```
