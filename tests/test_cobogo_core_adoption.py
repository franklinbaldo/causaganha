from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
VENDOR = WEB / "src" / "styles" / "vendor"


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def test_cobogo_core_vendor_is_verbatim_pinned_upstream_blob() -> None:
    pin = json.loads((VENDOR / "cobogo-core.pin.json").read_text(encoding="utf-8"))
    core = (VENDOR / "cobogo-core.css").read_bytes()

    assert pin["repository"] == "https://github.com/franklinbaldo/cobogo"
    assert pin["commit"] == "12b08d124d717e0a38f74d98b628ce9af0540a7b"
    assert pin["path"] == "src/styles/core.css"
    assert _git_blob_sha1(core) == pin["git_blob_sha1"]


def test_cobogo_core_loads_before_consumer_mapping_and_local_css() -> None:
    index_css = (WEB / "src" / "index.css").read_text(encoding="utf-8")

    core = index_css.index("./styles/vendor/cobogo-core.css")
    mapping = index_css.index("./styles/cobogo-mapping.css")
    local = index_css.index("./styles/base.css")

    assert core < mapping < local


def test_shared_accessibility_contracts_are_not_duplicated_locally() -> None:
    base_css = (WEB / "src" / "styles" / "base.css").read_text(encoding="utf-8")

    assert "\n:focus-visible {" not in base_css
    assert "@media (prefers-reduced-motion: reduce)" not in base_css


def test_page_header_does_not_duplicate_primary_site_navigation() -> None:
    site_nav = (WEB / "src" / "components" / "SiteNav.astro").read_text(encoding="utf-8")
    page_header = (WEB / "src" / "components" / "PageHeader.astro").read_text(encoding="utf-8")

    for label in (
        "Consultar processo",
        "Pesquisar publicações",
        "Minhas consultas",
        "Explorar cobertura",
        "Usar com agente",
        "Projeto & dados",
    ):
        assert label in site_nav

    assert "primaryLinks" not in page_header
    assert "ferramentasLinks" not in page_header
    assert "data-nav-drawer-trigger" not in page_header
    assert 'aria-label="Contexto da página"' in page_header
