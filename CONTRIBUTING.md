# Contributing to CausaGanha

Thank you for your interest in contributing to CausaGanha! This document outlines the constraints and requirements for contributing to the project, especially regarding our data pipeline and Internet Archive uploads.

## Internet Archive (IA) Upload Constraints

**CRITICAL: Do not replace `httpx` with `boto3` for Internet Archive uploads.**

Our data pipeline uses the Internet Archive S3-compatible API. While it looks like standard S3, it has specific requirements that are incompatible with the default behavior of `boto3`:

1.  **Metadata Headers**: IA requires metadata headers to be prefixed with `x-archive-meta-*`. `boto3` hardcodes these to `x-amz-meta-*`, which IA ignores or rejects.
2.  **HTTP 411 Errors**: `boto3` often fails to set `Content-Length` correctly for IA's frontend, resulting in `HTTP 411 (Length Required)` errors.
3.  **History**: We have attempted to migrate to `boto3` twice, and both times it broke the pipeline (see PR #348).

Always use `httpx` or a direct HTTP client for IA interactions. For more details, refer to [Internet Archive Upload Architecture](docs/architecture/internet-archive-upload.md).

## Testing Requirements

Before merging any changes that affect the upload logic:

1.  **Local Verification**: Run the collection script locally with your IA credentials:
    ```bash
    export IAS3_ACCESS_KEY="your_key"
    export IAS3_SECRET_KEY="your_secret"
    python scripts/pipeline/collect.py --max-items 1 --date 2026-01-01 --tribunal STF
    ```
2.  **Verify Metadata**: Check the IA item metadata after upload to ensure all `x-archive-meta-*` headers are correctly processed by IA.
3.  **No Regressions**: Ensure that the `Content-MD5` check still passes and that retries are handled gracefully.

## Development Workflow

1.  Fork the repository.
2.  Create a feature branch.
3.  Ensure code follows `ruff` linting rules.
4.  Submit a Pull Request with a clear description of the changes.

## Security

Do not commit any credentials (`ia.ini`, `.env`, or hardcoded keys). Use environment variables for local testing.
