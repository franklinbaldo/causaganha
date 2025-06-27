# CausaGanha CLI Design

## Overview

The CausaGanha CLI provides a modular, tribunal-agnostic system for processing judicial documents through a 4-stage pipeline. Built with Typer for modern Python CLI experience, it supports both granular control and convenient full-pipeline execution.

## Architecture

### Core Pipeline Stages

1. **Queue** - Add documents to processing queue from various sources
2. **Archive** - Download documents and store permanently in Internet Archive
3. **Analyze** - Extract information using LLM and save to DuckDB
4. **Score** - Generate OpenSkill ratings from parsed data

### Command Structure

```
causaganha
├── queue      # Add documents to processing queue
├── archive    # Download and store documents to IA
├── analyze    # Extract information with LLM
├── score      # Generate OpenSkill ratings
├── pipeline   # Run full pipeline (queue->archive->analyze->score)
├── stats      # Show processing statistics
└── config     # Configuration management
```

## Usage Examples

### Individual Commands

```bash
# Add single URL to queue (auto-detect everything from URL)
causaganha queue --url "https://www.tjro.jus.br/diario20250626.pdf"

# Add bulk from CSV file
causaganha queue --from-csv urls.csv

# Process queued items through each stage
causaganha archive  # Download and upload to IA
causaganha analyze  # Extract with LLM
causaganha score    # Calculate ratings

# Check progress
causaganha stats
```

### Pipeline Command (Convenience)

```bash
# Run full pipeline from CSV file
causaganha pipeline --from-csv urls.csv

# Resume interrupted pipeline
causaganha pipeline --resume

# Run specific stages only
causaganha pipeline --stages archive,analyze,score

# Stop on first error
causaganha pipeline --from-csv urls.csv --stop-on-error
```

## Input Formats

### CSV Format (urls.csv)
```csv
url
https://www.tjro.jus.br/diario20250626.pdf
https://www.tjro.jus.br/diario20250627.pdf

# Or with optional date override
url,date
https://www.tjro.jus.br/diario1.pdf,2025-06-26
https://www.tjro.jus.br/diario2.pdf,
```

**Auto-Detection**: Everything extracted from URL:
- `tribunal`: From domain (`tjro.jus.br` → `TJRO`)
- `date`: From URL patterns or filename
- `filename`: From URL path or HTTP headers

## DuckDB Schema

### Job Queue Table
```sql
CREATE TABLE job_queue (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    date DATE NOT NULL,
    tribunal TEXT NOT NULL,
    filename TEXT NOT NULL,
    metadata JSON,
    status TEXT DEFAULT 'queued',  -- queued, archived, analyzed, scored, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    ia_identifier TEXT,           -- Set after successful archive
    analyze_result JSON,          -- Set after successful analyze
    score_updated BOOLEAN DEFAULT FALSE  -- Set after successful score
);
```

### Processing States

- **queued** - Added to queue, ready for processing
- **archived** - Successfully downloaded and stored in IA
- **analyzed** - LLM extraction completed, data in DuckDB
- **scored** - OpenSkill ratings calculated and updated
- **failed** - Processing failed (with error_message)

## Features

### Progress Tracking
- tqdm progress bars for all long-running operations
- Real-time statistics showing items in each stage
- ETA calculations and throughput metrics

### Error Handling
- Automatic retry with exponential backoff
- Detailed error logging and reporting
- Resume capability from any stage
- Graceful handling of interruptions

### Modularity
- Each stage can run independently
- Support for multiple tribunals through external URL generation
- Flexible input formats (URL, JSON, CSV)
- Configurable concurrency and rate limiting

### Stats System
```bash
causaganha stats
# Output:
# Pipeline Status:
# ├── Queued:     1,250 items
# ├── Archived:   1,100 items  
# ├── Analyzed:     950 items
# ├── Scored:       800 items
# └── Failed:        25 items
# 
# Processing Speed:
# ├── Archive:  15 items/min
# ├── Analyze:   8 items/min  
# └── Score:    20 items/min
```

## Configuration

### Environment Variables
```bash
GEMINI_API_KEY=your_gemini_key
IA_ACCESS_KEY=your_ia_access_key
IA_SECRET_KEY=your_ia_secret_key
DUCKDB_PATH=data/causaganha.duckdb
```

### Config File (~/.causaganha/config.toml)
```toml
[processing]
max_workers = 5
max_retries = 3
rate_limit_rps = 2

[storage]
ia_collection = "causaganha"
temp_dir = "/tmp/causaganha"

[llm]
model = "gemini-2.5-flash"
max_tokens = 8192
temperature = 0.1
```

## Implementation Notes

### Technology Stack
- **Typer**: Modern Python CLI framework
- **DuckDB**: Job queue and data storage
- **tqdm**: Progress bars and status display
- **aiohttp**: Async HTTP operations
- **asyncio**: Concurrent processing

### Tribunal Agnostic Design
The CLI separates tribunal-specific URL discovery (Step 0) from the generic processing pipeline:

1. **External Step**: Generate URLs for any tribunal (TJRO, TJSP, etc.)
2. **Generic Pipeline**: Process URLs regardless of source tribunal
3. **Smart Detection**: Auto-extract tribunal and metadata from URLs
4. **Flexible Input**: Support various metadata formats per tribunal

**Auto-Detection Examples**:
- `https://www.tjro.jus.br/diario.pdf` → `tribunal: TJRO`
- `https://www.tjsp.jus.br/diario.pdf` → `tribunal: TJSP`
- `diario20250626.pdf` → `date: 2025-06-26`
- `20250626614-NR115.pdf` → `date: 2025-06-26, edition: 115`

This design allows easy extension to new tribunals without modifying core processing logic.

### Atomic Operations
Each document is processed as an atomic unit:
- State transitions are transactional
- Failed items can be retried independently  
- Pipeline can be safely interrupted and resumed
- No partial states or data corruption

## Future Enhancements

### HTTP Dashboard
- Real-time monitoring via web interface
- Job control (pause, resume, cancel)
- Historical statistics and charts
- API for programmatic access

### Advanced Features
- Priority queues for urgent processing
- Distributed processing across multiple machines
- Webhook notifications for completion
- Integration with CI/CD pipelines