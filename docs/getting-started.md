# Getting Started

This guide will walk you through the initial setup and a basic run of the CausaGanha pipeline.

## 1. Installation

CausaGanha is managed with `uv`, a fast Python package installer and resolver.

### Prerequisites

- Python 3.11+
- `git` for cloning the repository

### Steps

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/franklinbaldo/causaganha.git
    cd causaganha
    ```

2.  **Install Dependencies:**

    Use `uv` to sync the environment with the project's dependencies.

    ```bash
    uv sync --dev
    ```

3.  **Install in Editable Mode:**

    This makes the `causaganha` CLI command available in your shell.
    ```bash
    uv pip install -e .
    ```

## 2. Configuration

CausaGanha uses environment variables for configuration.

1.  **Create an Environment File:**

    Copy the example file to create your own local configuration:

    ```bash
    cp .env.example .env
    ```

2.  **Add Your API Key:**

    Open the `.env` file and add your Google Gemini API key:

    ```env
    GEMINI_API_KEY="your-api-key-here"
    ```

    !!! tip
        For more advanced settings, see the [Configuration](configuration.md) page.

## 3. Quick Run

Now you're ready to run the entire CausaGanha pipeline.

1.  **Initialize the Database:**

    This command creates the necessary tables in the local DuckDB database.

    ```bash
    uv run causaganha db init
    ```

2.  **Run the Pipeline:**

    The `pipeline` command runs all steps: `collect`, `archive`, `analyze`, and `score`.

    ```bash
    uv run causaganha pipeline --analyze-limit 5 --archive-limit 5
    ```

    This command will:
    - Collect intimations from yesterday.
    - Archive up to 5 documents.
    - Analyze up to 5 decisions.
    - Recalculate lawyer scores.

Congratulations! You've successfully run your first CausaGanha pipeline. To explore the CLI in more detail, check out the [CLI Reference](cli.md).
