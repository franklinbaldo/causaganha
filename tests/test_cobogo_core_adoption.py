from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def test_cobogo_is_a_real_panda_preset_dependency() -> None:
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    dev = package["devDependencies"]

    assert dev["@pandacss/dev"].startswith("^")
    assert dev["cobogo"] == ("github:franklinbaldo/cobogo#8ad1fe1c40bb6af12d8b8fcbe1b20d070b5bb44c")
    assert "@picocss/pico" not in package.get("dependencies", {})


def test_panda_config_loads_cobogo_preset() -> None:
    config = (WEB / "panda.config.ts").read_text(encoding="utf-8")

    assert "from 'cobogo/preset'" in config
    assert "presets: [cobogo]" in config
    assert "outdir: 'styled-system'" in config
    assert "./src/**/*.{astro,js,jsx,ts,tsx}" in config


def test_legacy_vendored_cobogo_is_not_loaded() -> None:
    index_css = (WEB / "src" / "index.css").read_text(encoding="utf-8")

    assert "vendor/cobogo-core.css" not in index_css
    assert "cobogo-mapping.css" not in index_css
    assert "@picocss/pico" not in index_css
    assert "@layer reset, base, tokens, recipes, utilities" in index_css


def test_global_shell_uses_generated_cobogo_apis() -> None:
    layout = (WEB / "src" / "layouts" / "Layout.astro").read_text(encoding="utf-8")

    assert "../../styled-system/css" in layout
    assert "../../styled-system/recipes" in layout
    assert "navLink" in layout
    assert "SiteNav" not in layout
    assert "Footer" not in layout


def test_primary_query_state_semantics_remain_shared() -> None:
    index_css = (WEB / "src" / "index.css").read_text(encoding="utf-8")
    styles = (WEB / "src" / "styles" / "query-states.css").read_text(encoding="utf-8")

    assert "@import './styles/query-states.css';" in index_css
    assert ".processo-lookup, .publication-search" in styles
    assert ".empty-state, .empty-search" in styles
    assert "[role='alert']" in styles
