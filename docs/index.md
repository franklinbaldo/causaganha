# Welcome to CausaGanha V2

**CausaGanha** is a distributed judicial analysis platform designed to collect, analyze, and score legal decisions at scale. It leverages modern technologies to provide insights into legal proceedings and lawyer performance.

This documentation covers the V2 architecture, which is a complete rewrite focused on scalability, modularity, and a modern CLI interface.

## Key Features

- **CLI-First Design**: A powerful and intuitive command-line interface for running the entire pipeline.
- **Modular Architecture**: A clear separation of concerns between data collection, analysis, storage, and scoring.
- **Asynchronous Processing**: Built with `asyncio` for high-performance I/O operations.
- **AI-Powered Analysis**: Integrates with large language models (LLMs) via Pydantic-AI to extract structured data from unstructured legal documents.
- **Pluggable Storage**: Uses the Ibis framework to abstract database interactions, with DuckDB as the default backend.

## Getting Started

Ready to dive in? Head over to the **[Getting Started](getting-started.md)** guide to install CausaGanha and run your first analysis.
