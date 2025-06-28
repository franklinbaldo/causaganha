# Async Pipeline Architecture

This document outlines the updated asynchronous processing pipeline used by CausaGanha.

![Async Pipeline Diagram](diagrams/async_pipeline.mermaid)

The pipeline now includes a **Download Orchestrator** that feeds download tasks to worker coroutines. This queue-based approach improves concurrency control and paves the way for future distributed job scheduling.

Key stages:
1. **Queue CSV URLs** – Source list of diarios ready for processing.
2. **Download Orchestrator** – Manages an `asyncio.Queue` of download jobs and dispatches them to the Downloader workers.
3. **Downloader** – Retrieves PDFs and stores them in Internet Archive.
4. **Gemini Analysis** – Extracts structured data from PDFs.
5. **DuckDB Database** – Persists extracted data.
6. **OpenSkill Scoring** – Updates lawyer ratings based on new decisions.

Concurrency levels for downloads and uploads remain configurable via command line options or environment variables.
