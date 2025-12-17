# Vendored API Specifications

This folder contains **vendored** API specifications used by CausaGanha to make development easier (schema validation, client generation, contract tests), and to reduce reliance on live network calls.

## PJe Comunica API (CNJ) — DJEN swagger

- **Origin**: `https://comunicaapi.pje.jus.br/swagger/djen.yml`
- **Vendored file**: `openapi/pje-comunicaapi-djen.swagger.yml`

### Updating the spec

The upstream host may be **geo-blocked** in some environments (including GitHub-hosted runners). We provide a GitHub Actions workflow that can fetch the spec and commit the updated file.

1. Run: **Actions → Vendor PJe Swagger → Run workflow**
2. If the origin is blocked, first mirror the YAML somewhere reachable and run the workflow with the mirror URL.

Alternatively, you can download it manually and update locally:

```bash
uv run python scripts/vendor_pje_swagger.py --input-file /path/to/djen.yml
git add openapi/pje-comunicaapi-djen.swagger.yml
git commit -m "chore(openapi): vendor PJe DJEN swagger"
git push
```
