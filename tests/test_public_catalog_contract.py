from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_workflow_publishes_text_contract_not_duckdb_binary() -> None:
    workflow = (ROOT / ".github/workflows/update-catalog.yml").read_text(encoding="utf-8")

    assert "generate_catalog.py --output ./catalog" in workflow
    assert "! -name '*.duckdb'" in workflow
    assert "generate_catalog.py --upload" not in workflow
    assert "cp docs/CATALOG.md catalog/README.md" in workflow


def test_public_surfaces_use_catalog_sql() -> None:
    paths = [
        ROOT / "web/src/pages/sobre.astro",
        ROOT / "web/src/components/DataAccessPanel.svelte",
    ]

    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "catalog.sql" in content
        assert "archive.org/download/causaganha-catalog/catalog.duckdb" not in content


def test_catalog_documentation_explains_consumer_owned_materialization() -> None:
    docs = (ROOT / "docs/CATALOG.md").read_text(encoding="utf-8")

    assert "catalog.sql" in docs
    assert "duckdb causaganha.duckdb < catalog.sql" in docs
    assert "not distributed as a canonical `.duckdb`" in docs
