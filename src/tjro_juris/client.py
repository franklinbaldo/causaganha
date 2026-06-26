"""JURIS TJRO HTTP client — search and aggregations."""

from __future__ import annotations

import html as htmllib
import re

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
    """POST to JURIS endpoint. tipo MUST be wrapped in list."""
    body: dict = {
        "from": from_,
        "size": size,
        "fields": {"tipo": [tipo]},
        "sort": [],
        "token": "",
    }
    if texto:
        body["fields"]["ds_modelo_documento"] = texto

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
