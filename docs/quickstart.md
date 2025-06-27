# Quickstart Guide

This guide shows how to get CausaGanha running quickly with the modern CLI.

## Prerequisites

1. **Python 3.10+** installed
2. **uv** package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **Environment variables** (create `.env` file):
   ```bash
   GEMINI_API_KEY=your_gemini_api_key_here    # Required for analyze stage
   IA_ACCESS_KEY=your_ia_access_key_here      # Required for archive stage  
   IA_SECRET_KEY=your_ia_secret_key_here      # Required for archive stage
   ```
   
   ⚠️ **Important**: The `GEMINI_API_KEY` is **required** for the analyze stage. Without it, extraction will fail and no valid data will be available for scoring. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Installation

1. **Clone and setup:**
   ```bash
   git clone https://github.com/franklinbaldo/causa_ganha.git
   cd causa_ganha
   uv sync --dev
   ```

2. **Initialize database:**
   ```bash
   uv run --env-file .env causaganha db migrate
   ```

## Basic Usage

### 1. Queue Documents

Create a CSV file with URLs (only .jus.br domains allowed):

```csv
url
https://www.tjro.jus.br/diario20250626.pdf
https://www.tjsp.jus.br/diario20250627.pdf
```

Queue for processing:
```bash
uv run --env-file .env causaganha queue --from-csv diarios.csv
```

### 2. Run Pipeline

Process all stages automatically:
```bash
uv run --env-file .env causaganha pipeline --from-csv diarios.csv
```

Or run stages individually:
```bash
# Download and archive to Internet Archive
uv run --env-file .env causaganha archive --limit 5

# Extract information with Gemini LLM  
uv run --env-file .env causaganha analyze --limit 5

# Calculate OpenSkill ratings
uv run --env-file .env causaganha score
```

### 3. Monitor Progress

Check pipeline status:
```bash
uv run --env-file .env causaganha stats
```

Example output:
```
📊 Pipeline Status:
├── ⏳ Queued: 10 items
├── 📦 Archived: 8 items  
├── 🔍 Analyzed: 5 items
├── ⭐ Scored: 3 items
└── ❌ Failed: 0 items
```

## Database Management

```bash
# Check database status
uv run --env-file .env causaganha db status

# Sync with Internet Archive shared database
uv run --env-file .env causaganha db sync

# Create backup
uv run --env-file .env causaganha db backup

# View configuration
uv run --env-file .env causaganha config
```

## Advanced Usage

### Resume Interrupted Processing
```bash
uv run --env-file .env causaganha pipeline --resume
```

### Run Specific Stages
```bash
uv run --env-file .env causaganha pipeline --stages archive,analyze
```

### Force Reprocessing  
```bash
uv run --env-file .env causaganha archive --force
uv run --env-file .env causaganha score --force
```

### Limit Processing
```bash
uv run --env-file .env causaganha pipeline --from-csv diarios.csv --limit 10
```

## What Happens During Processing

1. **Queue**: URLs are validated (.jus.br only) and metadata extracted
2. **Archive**: PDFs downloaded and uploaded to Internet Archive
3. **Analyze**: Gemini LLM extracts judicial decisions and lawyer information
4. **Score**: OpenSkill ratings calculated for lawyer performance

## Getting Help

```bash
uv run causaganha --help           # Main help
uv run causaganha queue --help     # Command-specific help
uv run causaganha pipeline --help  # Pipeline options
```

## Troubleshooting

- **Missing API keys**: Ensure `.env` file has all required keys
- **Gemini extraction fails**: Verify `GEMINI_API_KEY` is valid. Test with: `curl -H "Content-Type: application/json" -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$GEMINI_API_KEY" -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'`
- **No data for scoring**: If analyze stage produces no valid decisions, check Gemini API configuration. Dummy data is automatically filtered out during scoring.
- **Database errors**: Run `causaganha db migrate` to initialize/update schema
- **Import errors**: Run `uv sync` to ensure all dependencies installed
- **Permission errors**: Check IA credentials have upload permissions

## Next Steps

- Check [CLI Design](cli_design.md) for complete command reference
- See [Architecture Overview](../CLAUDE.md) for system details
- Review [OpenSkill Documentation](openskill.md) for rating system details