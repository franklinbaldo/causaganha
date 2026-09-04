from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_footer_links_use_the_wrapping_list_contract() -> None:
    footer = (WEB / "src" / "components" / "Footer.astro").read_text(encoding="utf-8")
    navigation = (WEB / "src" / "styles" / "navigation.css").read_text(encoding="utf-8")

    assert '<nav aria-label="Links do rodapé" class="footer-nav">' in footer
    assert footer.count("<li>") == 5
    assert "<ul>" in footer
    assert "</ul>" in footer
    assert ".site-footer nav ul" in navigation
    assert "flex-wrap: wrap" in navigation
