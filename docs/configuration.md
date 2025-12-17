# Configuration

CausaGanha is configured using environment variables. The recommended way to manage these is by creating a `.env` file in the root of the project.

You can create one by copying the example file:
```bash
cp .env.example .env
```

## Environment Variables

### `GEMINI_API_KEY`

This is the only **required** environment variable for the core analysis functionality. CausaGanha uses the Google Gemini models via `pydantic-ai` to analyze legal decisions.

-   **Required**: Yes
-   **Purpose**: Authentication for the LLM service.
-   **Example**: `GEMINI_API_KEY="your-google-ai-studio-key"`

!!! danger "Security"
    Never commit your `.env` file or expose your API keys in public repositories. The `.gitignore` file is already configured to ignore `.env`.

### `DB_PATH`

This variable specifies the path to the DuckDB database file. If not set, it defaults to a local file in the project directory.

-   **Required**: No
-   **Default**: `data/causaganha.duckdb`
-   **Purpose**: Defines where the application data is stored.
-   **Example**: `DB_PATH="/path/to/your/database.duckdb"`

### Internet Archive Keys (Optional)

The `archive` command is designed to upload documents to the Internet Archive for long-term storage and public access. However, it can also function in a "local-only" mode.

-   `IA_ACCESS_KEY`: Your Internet Archive access key.
-   `IA_SECRET_KEY`: Your Internet Archive secret key.

#### Behavior without Keys

If `IA_ACCESS_KEY` and `IA_SECRET_KEY` are **not** set in the environment:

- The `archive` command will still download the document PDFs.
- It will store them in a local directory (`data/archive/` by default).
- **No upload to the Internet Archive will occur.**

This allows for local development and testing of the `archive` and `analyze` steps without needing Internet Archive credentials.

!!! info
    When running the `archive` command, the system will log a warning if the IA keys are missing, confirming that it is operating in local-only mode.
