# DJEN API Documentation

## Overview

The DJEN (Diário de Justiça Eletrônico Nacional) is Brazil's national electronic judicial gazette system. It provides a REST API with **structured data** about judicial communications, lawyers, parties, and cases.

**Base URL**: `https://comunicaapi.pje.jus.br` (geo-blocked, use proxy)
**Proxy URL**: `https://djen-proxy-mhgmawcn3a-rj.a.run.app`
**OpenAPI Spec**: `openapi/pje-comunicaapi-djen.swagger.yml`

## Why DJEN is Valuable

Unlike scraping PDFs, DJEN provides **already structured data**:

| Data Type | Available Fields |
|-----------|------------------|
| **Lawyers** | OAB number, name, state, role in case |
| **Parties** | Name, CPF/CNPJ, role (plaintiff/defendant) |
| **Communications** | Type, date, content, court |
| **Cases** | Process number, court, class, subject |

This eliminates expensive LLM parsing - we get structured lawyer/party data directly from the API.

## Key Endpoints

### 1. Get Caderno (Daily Digest)

Downloads all communications for a court on a specific date.

```bash
GET /api/v1/caderno/{tribunal}/{date}/{tipo}

# Example: Get TJRO communications for Jan 15, 2026
curl "https://djen-proxy.../api/v1/caderno/TJRO/2026-01-15/D"
```

**Response:**
```json
{
  "url": "https://..../TJRO-2026-01-15.zip",
  "total_comunicacoes": 1523,
  "versao": 1
}
```

The ZIP contains JSON files with all communications for that day.

### 2. Search Communications

Search across all courts with filters.

```bash
GET /api/v1/comunicacao

# Parameters:
# - numeroOab: OAB number (e.g., "12345")
# - ufOab: OAB state (e.g., "SP")
# - nomeAdvogado: Lawyer name
# - nomeParte: Party name
# - numeroProcesso: Case number
# - siglaTribunal: Court code
# - dataDisponibilizacaoInicio: Start date (YYYY-MM-DD)
# - dataDisponibilizacaoFim: End date (YYYY-MM-DD)
```

**Example: Find all communications for a lawyer**
```bash
curl "https://djen-proxy.../api/v1/comunicacao?numeroOab=12345&ufOab=SP"
```

### 3. Authentication (Optional)

Some endpoints require CNJ/SCA credentials.

```bash
POST /api/v1/login
Content-Type: application/json

{
  "username": "your_cnj_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Data Structure

### Communication (Comunicação)

```json
{
  "id": 123456789,
  "numeroProcesso": "0001234-56.2026.8.22.0001",
  "numeroProcessoCommascara": "0001234-56.2026.8.22.0001",
  "siglaTribunal": "TJRO",
  "dataDisponibilizacao": "2026-01-15",
  "tipoComunicacao": "Intimação",
  "texto": "Fica V.Sa. intimado para...",
  "advogados": [
    {
      "numeroOab": "12345",
      "ufOab": "SP",
      "nome": "João da Silva"
    }
  ],
  "partes": [
    {
      "nome": "Empresa XYZ Ltda",
      "tipo": "Autor",
      "documento": "12.345.678/0001-90"
    },
    {
      "nome": "Fulano de Tal",
      "tipo": "Réu",
      "documento": "123.456.789-00"
    }
  ]
}
```

### Lawyer (Advogado)

```json
{
  "numeroOab": "12345",
  "ufOab": "SP",
  "nome": "João da Silva",
  "tipoParte": "Advogado do Autor"
}
```

### Party (Parte)

```json
{
  "nome": "Empresa XYZ Ltda",
  "tipo": "Autor",
  "documento": "12.345.678/0001-90",
  "tipoPessoa": "Jurídica"
}
```

## Rate Limits

The API has rate limiting:

| Header | Description |
|--------|-------------|
| `x-ratelimit-limit` | Max requests per window |
| `x-ratelimit-remaining` | Remaining requests |
| `x-ratelimit-reset` | Window reset time |

**Limits:**
- ~10,000 results per query (paginated)
- Requests per minute vary by endpoint

## Using in CausaGanha

### Automatic Collection

GitHub Actions collects data every 5 minutes:

```yaml
# .github/workflows/archive-zips.yml
- name: Download caderno
  run: |
    curl "$DJEN_API/api/v1/caderno/$TRIBUNAL/$DATE/D" -o info.json
    URL=$(jq -r '.url' info.json)
    curl "$URL" -o caderno.zip
```

### Manual Queries

```bash
# Via CLI
causaganha collect --days-back 7

# Direct API call
curl "https://djen-proxy.../api/v1/comunicacao?siglaTribunal=TJSP&dataDisponibilizacaoInicio=2026-01-01"
```

## Finding Opponents and Parties

One powerful use case: **find all cases where two lawyers faced each other**.

```python
# Pseudocode
# 1. Get communications for lawyer A
comms_a = api.search(numeroOab="12345", ufOab="SP")

# 2. For each case, get all lawyers involved
for comm in comms_a:
    case_lawyers = comm["advogados"]
    opponents = [l for l in case_lawyers if l["numeroOab"] != "12345"]

    # 3. Now you know who lawyer A faced in each case
    for opponent in opponents:
        print(f"Case {comm['numeroProcesso']}: faced {opponent['nome']}")
```

## Swagger UI

Access interactive API documentation:

```
https://djen-proxy.../swagger/index.html
```

Or view the local spec:

```bash
# View OpenAPI spec
cat openapi/pje-comunicaapi-djen.swagger.yml
```

## Updating the Spec

The OpenAPI spec is vendored (copied) from DJEN. To update:

```bash
# Trigger workflow
gh workflow run vendor-pje-swagger.yml

# Or manually
curl https://comunicaapi.pje.jus.br/swagger/djen.yml > openapi/pje-comunicaapi-djen.swagger.yml
```

## Courts (Tribunais)

91 courts are available:

| Category | Courts |
|----------|--------|
| **Federal** | TRF1-TRF6 |
| **Superior** | STF, STJ, TST, TSE, STM |
| **State** | TJAC, TJAL, ..., TJTO (27 courts) |
| **Labor** | TRT1-TRT24 |
| **Electoral** | TREAC, TREAL, ..., TRETO (27 courts) |
| **Other** | CNJ, CNMP, TNU |

## Related Files

- `openapi/pje-comunicaapi-djen.swagger.yml` - OpenAPI specification
- `djen.yml` - Root spec file
- `.github/workflows/vendor-pje-swagger.yml` - Spec update workflow
- `docs/DJEN_PROXY.md` - Proxy documentation
