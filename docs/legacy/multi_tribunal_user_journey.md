# Multi-Tribunal User Journey

This document outlines how a legal researcher interacts with CausaGanha when processing diarios from multiple tribunais.

1. **Queue** diarios for all required tribunals using the CLI or a CSV import.
2. **Sync** with the shared database to check for existing entries.
3. **Analyze** content and store results to DuckDB.
4. **Review** analytics in the upcoming web dashboard to compare across tribunals.

Pain points discovered during interviews include confusion over tribunal codes and difficulty tracking progress across jurisdictions.
