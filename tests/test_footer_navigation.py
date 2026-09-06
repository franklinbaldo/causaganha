from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_footer_links_wrap_inside_the_global_shell() -> None:
    layout = (WEB / "src" / "layouts" / "Layout.astro").read_text(encoding="utf-8")

    assert 'aria-label="Rodapé"' in layout
    assert "flexWrap: 'wrap'" in layout
    assert "href={BASE + 'processo'}" in layout
    assert "href={BASE + 'publicacoes'}" in layout
    assert "href={BASE + 'sobre'}" in layout
