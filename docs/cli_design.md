# CausaGanha CLI Design

## Overview

The CausaGanha CLI provides a modular, tribunal-agnostic system for processing judicial documents through a 4-stage pipeline. Built with Typer for modern Python CLI experience, it supports both granular control and convenient full-pipeline execution.

## Architecture

### Core Pipeline Stages

1. **Queue** - Add documents to processing queue from various sources
2. **Store** - Download documents and store permanently in Internet Archive
3. **Parse** - Extract information using LLM and save to DuckDB
4. **Rate** - Generate TrueSkill ratings from parsed data

### Command Structure

```
causaganha
├── queue      # Add documents to processing queue
├── store      # Download and store documents to IA
├── parse      # Extract information with LLM
├── rate       # Generate TrueSkill ratings
├── pipeline   # Run full pipeline (queue->store->parse->rate)
├── stats      # Show processing statistics
└── config     # Configuration management
```

## Usage Examples

### Individual Commands

```bash
# Add single URL to queue
causaganha queue --url "https://tribunal.com/diario.pdf" --date 2025-06-26 --tribunal TJRO

# Add bulk from JSON file
causaganha queue --json-file diarios_tjro_2025.json

# Add bulk from CSV file  
causaganha queue --csv-file diarios_batch.csv

# Process queued items through each stage
causaganha store    # Download and upload to IA
causaganha parse    # Extract with LLM
causaganha rate     # Calculate ratings

# Check progress
causaganha stats
```

### Pipeline Command (Convenience)

```bash
# Run full pipeline from JSON input
causaganha pipeline --json-file diarios.json

# Resume interrupted pipeline
causaganha pipeline --resume

# Run specific stages only
causaganha pipeline --stages store,parse,rate

# Stop on first error
causaganha pipeline --json-file diarios.json --stop-on-error
```

## Input Formats

### JSON Format
```json
[
  {
    "url": "https://tribunal.com/diario20250626.pdf",
    "date": "2025-06-26", 
    "tribunal": "TJRO",
    "filename": "20250626614-NR115.pdf",
    "metadata": {
      "year": 2025,
      "edition": 115,
      "pages": 150
    }
  }
]
```

### CSV Format
```csv
url,date,tribunal,filename,metadata
https://tribunal.com/diario1.pdf,2025-06-26,TJRO,20250626614-NR115.pdf,"{""year"":2025,""edition"":115}"
https://tribunal.com/diario2.pdf,2025-06-27,TJRO,20250627615-NR116.pdf,"{""year"":2025,""edition"":116}"
```

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
    status TEXT DEFAULT 'queued',  -- queued, stored, parsed, rated, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    ia_identifier TEXT,           -- Set after successful store
    parse_result JSON,            -- Set after successful parse
    rating_updated BOOLEAN DEFAULT FALSE  -- Set after successful rate
);
```

### Processing States

- **queued** - Added to queue, ready for processing
- **stored** - Successfully downloaded and stored in IA
- **parsed** - LLM extraction completed, data in DuckDB
- **rated** - TrueSkill ratings calculated and updated
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
# ├── Stored:     1,100 items  
# ├── Parsed:       950 items
# ├── Rated:        800 items
# └── Failed:        25 items
# 
# Processing Speed:
# ├── Store:  15 items/min
# ├── Parse:   8 items/min  
# └── Rate:   20 items/min
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
3. **Flexible Input**: Support various metadata formats per tribunal

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