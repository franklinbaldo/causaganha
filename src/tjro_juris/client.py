"""JURIS TJRO HTTP client — search and aggregations."""

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
PAGE_SIZE = 400

_UA = "Mozilla/5.0 (causaganha/tjro-juris)"


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


def search(tipo: str, from_: int = 0, size: int = PAGE_SIZE, texto: str = "") -> dict:
    """POST to JURIS endpoint. tipo MUST be wrapped in list (string crashes server)."""
    body: dict = {
        "token": "",
        "tipo": [tipo],
        "texto": texto,
        "from": from_,
        "size": size,
    }

    log.debug("juris_search", tipo=tipo, from_=from_, size=size)
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            ENDPOINT,
            json=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": _UA,
            },
        )
        resp.raise_for_status()
        return resp.json()


def get_aggregations() -> dict:
    """GET aggregations from JURIS."""
    url = "https://juris-back.tjro.jus.br/search/agregacoes"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers={"Accept": "application/json", "User-Agent": _UA})
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
