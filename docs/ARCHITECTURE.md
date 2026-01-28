# System Architecture

CausaGanha has transitioned from an LLM-heavy "doc-reading" pipeline to a **structured data** ingestion and analysis engine powered by the DJEN (Diário de Justiça Eletrônico Nacional) API.

## 🏗️ High-Level Flow

```mermaid
graph TD
    A[DJEN API] -->|Daily Scraping| B(GitHub Actions)
    B -->|ZIP/Absent| C[Internet Archive]
    C -->|Completion Check| D[Consolidation Job]
    D -->|Daily Parquets| C
    C -->|Remote Query| E[Ibis + DuckDB]
    E -->|Analysis| F[Outcome Classification]
    F -->|Scoring| G[OpenSkill Ratings]
```

### 1. Ingestion & Storage (Internet Archive)

The pipeline uses **GitHub Actions** to query the DJEN API every 5 minutes.

- **Raw ZIPs**: Downloaded directly and uploaded to Internet Archive.
- **Absent Markers**: If a court has no journal for the day, an `.absent` file is uploaded to maintain a 91-item completion matrix.

### 2. Atomic Consolidation

A dedicated consolidation job waits for all 91 courts to be present (ZIP or Absent) then merges them into **Atomic Daily Parquets**. This optimizes query performance by reducing metadata overhead and enabling national-level deduplication.

### 3. Data Layer (Ibis + DuckDB)

We use **Ibis** as a portable dataframe expression language, allowing us to query Parquet files directly on IA or locally via **DuckDB**. This eliminates the need for a traditional heavy database.

### 4. Analysis & Rating

- **Classification**: Heuristics and lightweight ML models classify communications into outcomes (Win/Loss/Other).
- **OpenSkill**: A Bayesian rating system (similar to Elo) calculates lawyer ratings based on these historical outcomes.

## 🛠️ Tech Stack

- **Lanuage**: Python 3.12 (uv for package management)
- **Data**: Ibis, DuckDB, Parquet
- **Infrastructure**: Cloudflare Workers, R2, Internet Archive
- **CLI**: Typer
- **DevTools**: Pytest (BDD), Structlog
