# OpenAPI specs (vendored)

We keep external API OpenAPI definitions in-repo to make development easier (type generation, schema validation, and contract tests), and to reduce reliance on a live network during day-to-day work.

## PJe Comunica API (CNJ)

Target service: `https://comunicaapi.pje.jus.br/api/v1`

### Update the spec

From the repo root:

```bash
uv run python scripts/fetch_pje_openapi.py --output openapi/pje-comunicaapi-v1.openapi.json
```

Then commit the updated `openapi/pje-comunicaapi-v1.openapi.json`.

### Notes

- The service is fronted by CloudFront and may be **geo-blocked** in some environments (HTTP 403). If the fetch fails, run it from an allowed network (e.g., your local machine) and commit the result.

