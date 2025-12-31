# CausaGanha V2 🚀

> 🤖 **For AI Assistants**: See **`AGENTS.md`** for complete development instructions, including TDD workflow and architectural guidelines.

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![V2](https://img.shields.io/badge/architecture-v2-blue?style=for-the-badge)
![Coverage](https://img.shields.io/badge/coverage-80%25%2B-green?style=for-the-badge)

**CausaGanha V2** is a distributed judicial analytics platform designed to bring transparency to the Brazilian legal system. It automates the collection, analysis, and scoring of lawyer performance based on case outcomes.

## 🏛️ V2 Architecture

The new V2 architecture replaces web scraping with API-first data collection and introduces a modern, scalable stack:

1.  **Collection**: Fetches structured metadata from **PJe Communications API** (replacing V1 scraping).
2.  **Storage**: Uses **Ibis** and **DuckDB** for high-performance analytical queries.
3.  **Analysis**: Uses **Pydantic AI** (wrapping Google Gemini) to extract structured outcomes from PDF decisions.
4.  **Scoring**: Applies the **OpenSkill** algorithm to generate rankings.
5.  **Distribution**: Syncs the DuckDB database via **Internet Archive** for decentralized access.

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- `uv` (Fast Python package installer)

### Installation

```bash
# Clone the repository
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha

# Install dependencies
uv sync --dev
uv pip install -e .

# Configure environment variables
cp .env.example .env
# Edit .env with your Google Gemini API Key and IA Credentials
```

### Usage (CLI)

The `causaganha` CLI is the main entry point for all operations.

```bash
# 1. Initialize Database
uv run causaganha db init

# 2. Collect Intimations (defaults to yesterday)
uv run causaganha collect --courts TJRO

# 3. Analyze Decisions (requires GEMINI_API_KEY)
uv run causaganha analyze --limit 10

# 4. Score Lawyers
uv run causaganha score

# 5. Archive Documents (requires IA credentials)
uv run causaganha archive --limit 10

# OR Run the Full Pipeline
uv run causaganha pipeline --courts TJRO
```

## 🧪 Testing

We strictly follow TDD. To run tests:

```bash
# Run all tests
uv run pytest

# Run specific suite
uv run pytest tests/e2e/
```

## 📚 Documentation

Detailed documentation is available in the `docs/` directory and can be served locally:

```bash
uv run mkdocs serve
```

## 🏗️ Project Structure

```
src/causaganha/
├── api/          # PJe API Client
├── analysis/     # Pydantic AI Analyzer
├── cloud/        # Google Cloud Functions
├── domain/       # Pydantic Domain Models
├── pipeline/     # Orchestration Logic (Collect, Analyze, Score)
├── scoring/      # OpenSkill Rating System
├── services/     # Document & Archive Services
├── storage/      # Ibis/DuckDB Repository
└── cli.py        # CLI Entry Point
```

## License

MIT License.
