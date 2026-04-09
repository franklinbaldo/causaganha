# CausaGanha

![Collect ZIPs](https://github.com/franklinbaldo/causaganha/actions/workflows/collect-zips.yml/badge.svg)
![Last Deploy](https://github.com/franklinbaldo/causaganha/actions/workflows/deploy-dashboard.yml/badge.svg)
![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

**CausaGanha** is a judicial analytics platform that collects, archives, and analyzes data from the Brazilian DJEN (Diário de Justiça Eletrônico Nacional) to provide transparent lawyer performance ratings.

Our pipeline scrapes 91 Brazilian court websites daily, aggregates judicial data into a public archive, and serves an open analytics dashboard. This exposes lawyer track records, case outcomes, and litigation timelines, creating unprecedented transparency in the Brazilian legal market.

## [Live Dashboard](https://franklinbaldo.github.io/causaganha/)

## Why This Matters

### The Problem: Information Asymmetry

In Brazil's legal market, clients have no way to objectively evaluate lawyer performance before hiring. The information asymmetry is stark:

- **Lawyers know** their track record, specializations, and typical outcomes
- **Clients don't know** if a lawyer wins cases, how long cases take, or their expertise areas
- **Result**: Clients rely on referrals, advertising, or luck—not data

This asymmetry harms consumers and protects underperforming lawyers from market accountability.

### The Solution: Public Data, Made Accessible

DJEN (Diário de Justiça Eletrônico Nacional) publishes **every judicial communication** from all 91 Brazilian courts—thousands of documents daily. This data includes:

- Lawyer names and OAB (bar association) numbers
- Case outcomes: wins, losses, settlements
- Which parties lawyers represent
- Timeline of case progression

**This data is already public.** But it's scattered across 91 different court systems, published daily in formats designed for lawyers—not for analysis. No one has aggregated it to answer simple questions like "What is this lawyer's win rate?"

### Our Strategy: Archive Everything, Analyze Later

We're building a **complete historical archive** of DJEN data:

1. **Collect Daily**: Every 20 minutes, download judicial communications from all 91 courts
2. **Archive Permanently**: Upload to Internet Archive—free, permanent, public storage
3. **Convert to Analytics Format**: Transform raw data into Parquet (columnar, compressed, queryable)
4. **Build the Index**: Master catalog enables querying without downloading everything

**Why Internet Archive?**

- Free, unlimited storage
- Permanent URLs (data doesn't disappear)
- Public access (anyone can verify our data)
- Supports remote queries via HTTP range requests

**Why archive first, analyze later?**

- Data that isn't collected is lost forever
- Storage is cheap; re-collection is impossible
- Analysis methods improve; raw data doesn't
- Regulatory changes could restrict access

### Data Coverage

| Metric | Value |
| :----- | :---- |
| Courts monitored | 91 (all Brazilian jurisdictions) |
| Collection frequency | Every 20 minutes |
| Data format | JSON (raw) → Parquet (analytics) |
| Storage | Internet Archive (permanent) |
| Historical data | Building from 2024 onwards |

## Architecture

```mermaid
flowchart LR
    subgraph pipeline ["GitHub Actions Pipeline"]
        direction LR
        A["1. Collect ZIPs\n(Daily)"] --> B["2. Update Catalog\n(Post-collect)"]
        B --> C["3. Deploy Dashboard\n(Post-catalog)"]
    end

    A -.-> |"Scrape 91 courts\nUpload ZIPs"| IA1[("Internet Archive\n(Daily Items)")]
    B -.-> |"Generate catalog.json\n(Metadata + Stats)"| IA2[("Internet Archive\n(Master Catalog)")]
    C -.-> |"Astro/Svelte UI\nFetch from IA"| GH["GitHub Pages\nDashboard"]

    classDef workflow fill:#2d3748,stroke:#4a5568,color:#fff,stroke-width:2px;
    classDef storage fill:#2b6cb0,stroke:#2c5282,color:#fff,stroke-width:2px;
    classDef hosting fill:#276749,stroke:#22543d,color:#fff,stroke-width:2px;

    class A,B,C workflow;
    class IA1,IA2 storage;
    class GH hosting;
```

1. **Collect ZIPs** (daily workflow): scrapes 91 Brazilian court websites, downloads legal gazette ZIPs, and uploads them to the Internet Archive.
2. **Update Catalog** (runs after collect): generates catalog JSON with metadata (`tribunal_count`, `generated_at`), and uploads it to the Internet Archive.
3. **Deploy Dashboard** (runs after catalog): Astro/Svelte dashboard hosted on GitHub Pages showing pipeline status, tribunal coverage (91 courts), and run history.

## Tech Stack

### Backend (Python 3.12+)

| Layer | Technology | Purpose |
| :---- | :--------- | :------ |
| Runtime | [uv](https://docs.astral.sh/uv/) | Fast package manager & virtualenv |
| CLI | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) | Command-line interface |
| HTTP | [httpx](https://www.python-httpx.org/) | Async HTTP client (IA uploads, DJEN API) |
| Config | [Pydantic](https://docs.pydantic.dev/) + pydantic-settings | Data validation & env config |
| Logging | [structlog](https://www.structlog.org/) | Structured logging |
| Retry | [tenacity](https://tenacity.readthedocs.io/) | Resilient API calls |
| Data | [DuckDB](https://duckdb.org/) + [Ibis](https://ibis-project.org/) | Embedded OLAP DB + lazy query builder |
| Storage | [Apache Parquet](https://parquet.apache.org/) | Columnar analytics format |
| Vectors | [LanceDB](https://lancedb.github.io/lancedb/) | Embeddings vector store |
| AI/LLM | [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`) | Decision text analysis |
| AI Agent | [Pydantic AI](https://ai.pydantic.dev/) | Structured LLM output |
| Ratings | [OpenSkill](https://openskill.me/) | Elo-style lawyer performance ratings |
| Archive | [internetarchive](https://archive.org/developers/internetarchive.html) | Internet Archive client |
| Linter | [ruff](https://docs.astral.sh/ruff/) | Formatter + linter (all rules) |
| Testing | pytest + pytest-bdd + respx | Unit, BDD, and HTTP mock tests |

### Frontend (Dashboard)

| Layer | Technology | Purpose |
| :---- | :--------- | :------ |
| Framework | [Astro 5](https://astro.build/) | Static site generator (island architecture) |
| UI | [Svelte 5](https://svelte.dev/) | Reactive components |
| Analytics | [DuckDB WASM](https://duckdb.org/docs/api/wasm/overview.html) | Client-side SQL queries on Parquet |
| Charts | [Observable Plot](https://observablehq.com/plot/) | Data visualization |
| Build | [Vite](https://vite.dev/) | Module bundler |
| Tests | [Vitest](https://vitest.dev/) + Vitest-Cucumber | Unit + BDD tests |
| Hosting | [GitHub Pages](https://pages.github.com/) | Static site deployment |

### Infrastructure

| Component | Technology | Purpose |
| :-------- | :--------- | :------ |
| CI/CD | [GitHub Actions](https://github.com/features/actions) | Pipeline orchestration (every 20 min) |
| Data lake | [Internet Archive](https://archive.org/) | Permanent public Parquet/ZIP storage |
| DJEN proxy | [Google Cloud Run](https://cloud.google.com/run) (São Paulo) | Bypass DJEN geo-block |

---

## Development Status (V2 Refactoring)

We are currently refactoring the core architecture (V2) to improve scalability and maintainability.

**Current Focus:**
- **PJe API Integration**: Transitioning from legacy ZIP scraping to the direct PJe Communications API for real-time metadata collection.
- **CLI Decomposition**: Breaking down the monolithic CLI into modular subcommands for better maintainability.
- **Ibis Optimization**: Ensuring maximum leverage of Ibis lazy evaluation for 10-100x faster analytical queries.

**Active Threads:**
- `CG-0006`: CLI Refactoring (Catalog and Ground Truth).
- `CG-0008`: Ibis Lazy Evaluation Audit.
- `CG-0009`: PJe API Client integration into the main pipeline.

### Internet Archive (Consolidated Data Lake)

Since January 2026, we have transitioned from per-tribunal files to **consolidated daily Parquet files** to optimize query performance and reduce file metadata overhead.

#### IA Upload Strategy

To ensure reliability and compatibility with the Internet Archive S3 API, we use a custom upload strategy:

- **Library**: We use `httpx` instead of `boto3`.
- **Reasoning**: `boto3` generates AWS-specific headers and lacks proper support for IA's metadata requirements (leading to HTTP 411 errors).
- **Metadata**: All metadata headers use the `x-archive-meta-*` prefix.
- **Integrity**: Explicit `Content-MD5` headers are used for every upload.

For a detailed technical breakdown, see [Internet Archive Upload Architecture](docs/architecture/internet-archive-upload.md).

```text

djen-2026-01-27/
├── djen-2026-01-27-TJSP.zip   ← Raw source
├── djen-2026-01-27-TJRS.zip   ← Raw source
├── djen-2026-01-27-TJRS.absent ← Marker for empty journals
├── comunicacoes.parquet       ← Consolidated (all 91 courts)
├── advogados.parquet          ← Global identifiers (OAB+UF)
├── advogado_nomes.parquet     ← Lawyer name aliases
├── destinatarios.parquet      ← Communication recipients
├── comunicacao_advogados.parquet ← Lawyer-Communication links
├── representacoes.parquet     ← Materialized Lawyer-Party links
├── processos.parquet          ← Process activity index
├── textos.parquet             ← Content-addressed texts
├── partes.parquet             ← Normalized party dimension
├── classificacoes.parquet     ← Outcome labels per text
└── ...

```

## Data Schema

The consolidated data lake follows a future-proofed schema using deterministic **UUIDv5** identifiers for both communications and lawyers, enabling national-level deduplication and stable cross-referencing.

**Key design decisions:**

- **Lawyer identity = OAB + UF only** — Name is excluded from the identity hash to prevent accidental duplicates from spelling variants, accents, or marital name changes. Name aliases are tracked separately in `advogado_nomes`.
- **Content-addressed texts** — `textos.id` is `UUIDv5(full text)`, so identical judicial texts from different tribunals deduplicate to one row. Tribunal context is available via `comunicacoes.texto_id` joins.
- **Classification decoupled from communications** — `classificacoes` is keyed by `(texto_id, metodo)`, allowing multiple classification methods (LLM, RAG, manual) per text without column explosion.
- **Native date types** — `data_disponibilizacao` is `DATE`, `processed_at` and `classified_at` are `TIMESTAMP`, enabling partition pruning and time-window queries.
- **processos = activity index, not dimension** — One row per communication event (not one row per unique case). Join via `comunicacao_id` to get event types for temporal analytics.
- **Party entity resolution** — `partes` normalizes names (strip accents, uppercase, collapse whitespace) with `UUIDv5(normalized_name)` for best-effort deduplication. `destinatarios` and `representacoes` reference `parte_id`.

```mermaid
erDiagram
    comunicacoes ||--o{ destinatarios : "has"
    comunicacoes ||--o| textos : "links to"
    comunicacoes ||--o{ comunicacao_advogados : "notifies"
    comunicacoes ||--o{ representacoes : "m:n relationship"
    comunicacoes ||--o{ processos : "activity index"
    advogados ||--o{ comunicacao_advogados : "receives"
    advogados ||--o{ advogado_nomes : "aliases"
    advogados ||--o{ representacoes : "represents"
    partes ||--o{ destinatarios : "identifies"
    partes ||--o{ representacoes : "identifies"
    textos ||--o{ classificacoes : "classified by"

    comunicacoes {
        string id PK "UUIDv5 (Canonical JSON + Tribunal)"
        string original_id "Source ID"
        string tribunal
        string numero_processo
        date data_disponibilizacao
        timestamp processed_at
        string texto_id FK "Link to deduplicated text"
    }

    advogados {
        string id PK "UUIDv5 (OAB + UF)"
        string original_id "Source ID"
        string nome "Last seen name"
        string numero_oab
        string uf_oab
    }

    advogado_nomes {
        string advogado_id FK
        string nome "Name variant"
        string tribunal "Source tribunal"
        date first_seen
    }

    destinatarios {
        string comunicacao_id FK
        string nome "Party Name"
        string polo "Active/Passive"
        string parte_id FK "Normalized party"
    }

    partes {
        string id PK "UUIDv5 (Normalized Name)"
        string nome_normalizado "Uppercase, no accents"
        string nome_original "First occurrence"
    }

    representacoes {
        string comunicacao_id FK
        string advogado_id FK
        string parte_id FK "Normalized party"
        string polo "Active/Passive"
    }

    processos {
        string numero_processo
        string tribunal
        date data "Event date"
        string comunicacao_id FK "Source communication"
    }

    textos {
        string id PK "UUIDv5 (Full Text Content)"
        string texto "Full document body"
    }

    classificacoes {
        string texto_id FK
        string metodo "llm / rag / hybrid / manual"
        string outcome "procedente / improcedente / ..."
        string decision_type "sentenca / acordao / ..."
        string winner_advogado_id FK
        string loser_advogado_id FK
        float confidence
        timestamp classified_at
    }
```

## Data Pipeline

Data processing is orchestrated by three GitHub Actions workflows that form a chain: **Collect ZIPs** (`.github/workflows/collect-zips.yml`, every 20 min) → **Update Catalog** (`.github/workflows/update-catalog.yml`, on collect success) → **Deploy Dashboard** (`.github/workflows/deploy-dashboard.yml`, on catalog update):

| Step | Frequency | Description |
| :-- | :-------- | :---------- |
| **Collect** | Every 20 min | Download from DJEN → Upload ZIP/Absent to IA |
| **Consolidate** | Every 20 min | Atomic consolidation (waits for 91 markers) |
| **Embed** | Every 20 min | Generate vector embeddings (batch processed) |
| **Catalog** | As needed | Update master catalog (on file changes) |
| **Dashboard** | As needed | Update dashboard cache (on catalog update) |

Each step calls a Python script that can be run individually or via the orchestrator:

```bash
# Run full pipeline locally
uv run python scripts/pipeline/run.py

# Run specific step via orchestrator
uv run python scripts/pipeline/run.py --job collect --date 2026-01-27

# Run backfill via Python CLI
uv run causaganha backfill run --workers 4

# Run individual scripts for debugging
uv run python scripts/pipeline/consolidate.py --date 2026-01-27
uv run python scripts/pipeline/embed.py --max-decisions 100
uv run python scripts/generate_catalog.py --upload
```

See the workflow file for detailed documentation on architecture and configuration.

## DJEN API

The DJEN (Diário de Justiça Eletrônico Nacional) provides structured judicial communication data:

- **Lawyers**: OAB numbers, names
- **Parties**: Process parties (plaintiff, defendant)
- **Communications**: Intimations, citations, notifications
- **Processes**: Case numbers, courts, dates

**API Documentation**: See [docs/DJEN_API.md](docs/DJEN_API.md)

### Geo-blocking

The DJEN API is geo-blocked to Brazilian IPs. We use a reverse proxy on Google Cloud Run (São Paulo region) to bypass this restriction.

**Proxy URL**: `https://djen-proxy-mhgmawcn3a-rj.a.run.app`

See [docs/DJEN_PROXY.md](docs/DJEN_PROXY.md) for details.

## Quick Start

```bash
# Install dependencies
uv sync

# Initialize local database
causaganha db init

# Check database status
causaganha db status

# Download and analyze from Internet Archive
causaganha parquet download TJRO 2026-01-15
causaganha parquet analyze TJRO 2026-01-15
```

## Catalog System

The master catalog provides an index of all DJEN data on Internet Archive:

```bash
# Download catalog (< 10 MB)
causaganha catalog download

# Check what data is missing
causaganha catalog backfill-status

# Query the catalog
causaganha catalog query "SELECT * FROM manifest WHERE tribunal = 'TJSP' LIMIT 10"
```

Query remote data directly (no download needed):

```sql
-- Open catalog in DuckDB
duckdb causaganha-catalog/catalog.duckdb

-- Query remote Parquet files on Internet Archive
SELECT tribunal, COUNT(*) FROM comunicacoes GROUP BY tribunal;
```

See [docs/CATALOG.md](docs/CATALOG.md) for detailed documentation.

## Project Structure

```text
causaganha/

├── src/causaganha/          # Main Python package
│   ├── cli/                 # Typer CLI commands
│   ├── pipeline/            # Data pipeline (collect, analyze, score)
│   ├── analysis/            # AI analysis (LLM, RAG, embeddings)
│   ├── storage/             # DuckDB + Parquet storage
│   ├── scoring/             # OpenSkill rating algorithm
│   ├── catalog/             # DuckDB catalog generator
│   └── clients/             # External service clients
├── djen-scraper/            # DJEN scraping infrastructure
│   └── scripts/             # Conversion scripts
├── dashboard/               # Pipeline monitoring dashboard (Astro)
├── .github/workflows/       # GitHub Actions pipelines
├── docs/                    # Archived documentation
└── tests/                   # BDD and unit tests
```

## Internet Archive Structure

All data is publicly archived on Internet Archive:

| Item Pattern | Contents |
| :----------- | :------- |
| `djen-YYYY-MM-DD` | ZIPs, Parquets, and .absent markers for one day |
| `causaganha-catalog` | Master DuckDB catalog + manifest |
| `causaganha-embeddings-*` | Embedding vectors for semantic search |

## Development & How to Contribute

We welcome contributions to CausaGanha! This project is open-source and relies on the community to improve transparency in the Brazilian legal system.

Please see our comprehensive [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on:
- Setting up your development environment
- Project architecture and structure
- How to add a new tribunal scraper
- Our PR checklist and code style guidelines

### How to Run Locally

```bash
# Setup
uv venv && source .venv/bin/activate
uv sync --dev

# Run the project test suite
uv run pytest tests/

# Format and lint code
uv run ruff format
uv run ruff check --fix

# Initialize local database
causaganha db init

# See all CLI commands
causaganha --help
```

### Contributing

1. **Fork the repository.**
2. **Create a branch** for your feature or bug fix.
3. **Commit your changes**, keeping them focused and well-documented.
4. **Run linters and tests** before submitting to ensure pipeline compatibility.
5. **Open a Pull Request** with a descriptive title and detailed summary of your changes. Include context on what you are addressing (and link any related issues using `Refs <issue>`).

For more detailed developer guidance on the codebase structure and architecture rules, please see [CLAUDE.md](CLAUDE.md).

## License

MIT
