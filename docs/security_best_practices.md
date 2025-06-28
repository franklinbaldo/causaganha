# Security Best Practices for Contributors

This document outlines basic guidelines for keeping the CausaGanha ecosystem secure.

## Handling Secrets
- Never commit API keys or credentials to the repository.
- Store Internet Archive and Gemini keys in your `.env` file.
- Restrict permissions on configuration files to `600` when possible.

## Database Security
- Use encryption at rest for the local DuckDB file when storing sensitive data.
- Keep encryption keys outside of the repository and rotate them periodically.

## PDF Verification
- Validate the digital signature of each downloaded PDF before processing.
- Reject files with invalid or missing signatures to prevent tampering.

## Dependency Hygiene
- Run `pip-audit` regularly to check for known vulnerabilities.
- Keep dependencies up to date and pin versions in `pyproject.toml`.

Following these recommendations helps protect both data and infrastructure.
