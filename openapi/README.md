# Vendored API Specifications

This folder contains **vendored** API specifications used by CausaGanha to make development easier (schema validation, client generation, contract tests), and to reduce reliance on live network calls.

## PJe Comunica API (CNJ) — DJEN swagger

- **Origin**: `https://comunicaapi.pje.jus.br/swagger/djen.yml`
- **Vendored file**: `openapi/pje-comunicaapi-djen.swagger.yml`

### Updating the spec

The upstream host may be **geo-blocked** in some environments. We provide a GitHub Actions workflow that fetches the spec from a GitHub runner and commits the updated file:

1. Run: **Actions → Vendor PJe Swagger → Run workflow**
2. The workflow will update `openapi/pje-comunicaapi-djen.swagger.yml` and commit to `main` if it changed.

