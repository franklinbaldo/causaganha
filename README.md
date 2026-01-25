# CausaGanha

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

**CausaGanha** is a judicial analytics platform that uses structured data from the DJEN (Diário de Justiça Eletrônico Nacional) to provide transparent lawyer performance ratings.

## 📊 [Live Dashboard & Status](https://franklinbaldo.github.io/causaganha/)

## 🎯 Vision

Identify top-performing lawyers using real judicial outcomes, eliminating information asymmetry in the legal market.

## 🏗️ How it Works

1. **Ingest**: Structured data is pulled from the DJEN API via a distributed scraper.
2. **Normalize**: Data is stored as columnar Parquet files on the Internet Archive.
3. **Analyze**: Communications are classified to determine case outcomes and lawyer involvement.
4. **Rate**: Lawyers are rated using the **OpenSkill** algorithm.

## 🚀 Quick Start

```bash
# Install dependencies
uv sync

# Initialize database
causaganha db init

# Run the pipeline
causaganha pipeline --days-back 7
```

## 📂 Project Structure

- `src/causaganha/`: Main application logic.
- `djen-scraper/`: Continuous scraping infrastructure.
- `tests/`: BDD and unit test suite.

For detailed developer guidance, see [CLAUDE.md](CLAUDE.md).
