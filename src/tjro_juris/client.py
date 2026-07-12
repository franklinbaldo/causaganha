"""JURIS TJRO HTTP client — search and aggregations.

API contract (reverse-engineered from the portal's Next.js bundles, 2026-07):

- ``POST /search/varios_parametros/`` with body
  ``{"from": N, "size": M, "fields": {...}, "sort": [...]}``.
  Filters live under ``fields`` using Elasticsearch ``.raw`` keyword subfields
  (``tipo.raw``, ``ds_classe_judicial.raw``, ...). Free text goes in
  ``fields.query``; date range in ``fields.dtjulgamento_inicio`` /
  ``fields.dtjulgamento_fim`` (ISO ``YYYY-MM-DD``, inclusive).
  The old flat body (``{"token": "", "tipo": [...], "texto": ...}``) now
  returns HTTP 500.
- ``POST /search/agregacoes`` with body ``{"fields": {...}}`` (GET is 405).
- Pagination is capped by the Elasticsearch result window:
  ``from + size`` must stay <= ``MAX_RESULT_WINDOW`` (10 000) or the server
  returns HTTP 500. Callers that need more must slice by date window.
"""

from __future__ import annotations

import html as htmllib
import re
from urllib.parse import urlencode

import httpx
import structlog


log = structlog.get_logger()

TIPOS = [
    "ACÓRDÃO",
    "DECISÃO",
    "DECISÃO DA PRESIDÊNCIA",
    "SENTENÇA",
    "VOTO",
    "EMENTA",
    "RELATÓRIO",
]

ENDPOINT = "https://juris-back.tjro.jus.br/search/varios_parametros/"
AGGREGATIONS_ENDPOINT = "https://juris-back.tjro.jus.br/search/agregacoes"
PAGE_SIZE = 400

# Elasticsearch max_result_window: requests with from + size beyond this 500.
MAX_RESULT_WINDOW = 10_000

_UA = "Mozilla/5.0 (causaganha/tjro-juris)"
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": _UA,
}

# Crawl-stable ordering: newest first, score as tiebreak (mirrors the
# portal's "recentes" mode).
_SORT_RECENT = [{"dtjulgamento": "desc"}, {"_score": "desc"}]


def clean_html(html: str) -> str:
    """Remove base64 img tags, style, script blocks, all HTML tags, decode HTML entities."""
    if not html:
        return ""
    html = re.sub(r"<img[^>]*>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style[^>]*>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<script[\s\S]*?</script[^>]*>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = htmllib.unescape(html)
    return re.sub(r"\s+", " ", html).strip()


def search(
    tipo: str,
    from_: int = 0,
    size: int = PAGE_SIZE,
    texto: str = "",
    *,
    date_start: str | None = None,
    date_end: str | None = None,
) -> dict:
    """POST to the JURIS search endpoint.

    ``tipo`` is sent as ``fields["tipo.raw"]`` and MUST be wrapped in a list.
    ``texto`` maps to ``fields.query`` (free text). ``date_start`` /
    ``date_end`` are inclusive ISO dates mapped to ``dtjulgamento_inicio`` /
    ``dtjulgamento_fim``. Response is raw Elasticsearch (``hits.hits``).
    """
    fields: dict = {"tipo.raw": [tipo]}
    if texto:
        fields["query"] = texto
    if date_start:
        fields["dtjulgamento_inicio"] = date_start
    if date_end:
        fields["dtjulgamento_fim"] = date_end

    body: dict = {
        "from": from_,
        "size": size,
        "fields": fields,
        "sort": _SORT_RECENT,
    }

    log.debug("juris_search", tipo=tipo, from_=from_, size=size, date_start=date_start)
    with httpx.Client(timeout=30) as client:
        resp = client.post(ENDPOINT, json=body, headers=_HEADERS)
        resp.raise_for_status()
        return resp.json()


def get_aggregations() -> dict:
    """POST to the JURIS aggregations endpoint (GET returns 405)."""
    with httpx.Client(timeout=30) as client:
        resp = client.post(AGGREGATIONS_ENDPOINT, json={"fields": {}}, headers=_HEADERS)
        resp.raise_for_status()
        return resp.json()


PORTAL_URL = "https://juris.tjro.jus.br/jurisprudencia/"


def doc_url(
    id_processo_documento: int | str | None,
    *,
    sistema_origem: str = "",
    tipo: str = "",
    id_documento_principal: int | str | None = None,
) -> str:
    """Build portal URL with all required query parameters."""
    if id_processo_documento is None:
        return ""
    params: dict[str, str] = {"id": str(id_processo_documento)}
    if sistema_origem:
        params["sistema_origem"] = sistema_origem
    if tipo:
        params["tipo"] = tipo
    if id_documento_principal is not None:
        params["id_documento_principal"] = str(id_documento_principal)
    return f"{PORTAL_URL}?{urlencode(params)}"
