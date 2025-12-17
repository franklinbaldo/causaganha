# CLI Reference

The `causaganha` command-line interface is the primary way to interact with the judicial analysis pipeline.

## Global Options

-   `--verbose`, `-v`: Enable verbose logging for more detailed output.

## Commands

### `db`

Manages the database.

-   `causaganha db init`: Initializes the database and creates the required schema. This should be the first command you run.
-   `causaganha db status`: Shows the current connection status and lists the tables in the database.

### `collect`

Collects new intimations from the PJe API for a given date range and court.

```bash
uv run causaganha collect --start-date 2024-01-01 --end-date 2024-01-31 --courts TJRO
```

**Options:**

-   `--start-date`: The start of the date range (YYYY-MM-DD). Defaults to yesterday.
-   `--end-date`: The end of the date range (YYYY-MM-DD). Defaults to today.
-   `--courts`: A comma-separated list of court identifiers (e.g., `TJRO,TJSP`).

!!! warning "Geo-Blocking"
    The PJe API endpoint (`https://comunicaapi.pje.jus.br`) may be geo-blocked, returning a `403 Forbidden` error if accessed from outside Brazil. For development in affected regions, you may need to rely on mocked data from the integration tests.

### `archive`

Downloads and archives the PDF documents associated with collected intimations.

```bash
uv run causaganha archive --limit 20 --dry-run
```

**Options:**

-   `--limit`: The maximum number of documents to archive in this run.
-   `--dry-run`: Simulates the process without actually uploading to the Internet Archive.

!!! info "Local Fallback"
    If Internet Archive keys are not configured, this command will download documents to a local directory instead. See the [Configuration](configuration.md) page for details.

### `analyze`

Analyzes the content of downloaded documents using an LLM to extract structured data.

```bash
uv run causaganha analyze --limit 10
```

**Options:**

-   `--limit`: The maximum number of documents to analyze.

### `score`

Calculates and updates lawyer ratings using the OpenSkill algorithm based on the results of the analysis.

```bash
uv run causaganha score --limit 100
```

**Options:**

-   `--limit`: The maximum number of analysis results to process for scoring.

### `pipeline`

Runs the entire pipeline in sequence: `collect` → `archive` → `analyze` → `score`.

```bash
uv run causaganha pipeline --start-date 2024-01-01 --courts TJRO --analyze-limit 50
```

This command accepts options from all the individual commands, allowing you to customize the full run.

**Options to Skip Steps:**

-   `--skip-collect`
-   `--skip-archive`
-   `--skip-analyze`
-   `--skip-score`
