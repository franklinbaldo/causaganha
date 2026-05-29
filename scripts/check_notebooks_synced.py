#!/usr/bin/env python3
"""CI check: every marimo notebook has an up-to-date exported .ipynb.

Notebooks in ``notebooks/`` are authored as marimo notebooks (``*.py``), and
the committed ``*.ipynb`` is produced by ``marimo export ipynb`` followed by a
small post-processing step (see ``export_ipynb``) that drops the standalone
``import marimo as mo`` cell so the notebook runs in Colab.

This check re-runs that export for every marimo notebook and fails if the
committed ``.ipynb`` is missing or differs from a fresh export — i.e. the
generated Jupyter notebook is stale and must be regenerated and committed.

Usage:
    uv run python scripts/check_notebooks_synced.py            # check
    uv run python scripts/check_notebooks_synced.py --fix      # regenerate
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat


NOTEBOOK_DIR = Path(__file__).resolve().parent.parent / "notebooks"
# Match how the committed .ipynb files are produced. Keep in sync with the
# --fix path and with CONTRIBUTING docs.
EXPORT_SORT = "top-down"


def is_marimo_notebook(path: Path) -> bool:
    """A marimo notebook imports marimo and instantiates ``marimo.App``."""
    text = path.read_text(encoding="utf-8")
    return "import marimo" in text and "marimo.App(" in text


def export_ipynb(notebook: Path, out: Path) -> None:
    """Export ``notebook`` to a Colab-runnable Jupyter notebook at ``out``.

    Runs ``marimo export ipynb`` and then strips the standalone
    ``import marimo as mo`` cell that marimo emits: ``mo.md(...)`` cells are
    already exported as real markdown cells, so that import is dead code in
    the .ipynb and would raise ``ModuleNotFoundError`` in Colab (where marimo
    isn't installed). Both the check and the --fix paths go through here, so
    the committed .ipynb stays byte-identical to this output.
    """
    with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False) as tmp:
        raw = Path(tmp.name)
    try:
        subprocess.run(  # noqa: S603
            [
                "marimo",
                "export",
                "ipynb",
                str(notebook),
                "--sort",
                EXPORT_SORT,
                "-o",
                str(raw),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        nb = nbformat.read(raw, as_version=nbformat.NO_CONVERT)
        nb.cells = [
            c
            for c in nb.cells
            if not (
                c.get("cell_type") == "code"
                and c.get("source", "").strip() == "import marimo as mo"
            )
        ]
        nbformat.write(nb, str(out))
    finally:
        raw.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Regenerate the .ipynb files in place instead of just checking.",
    )
    args = parser.parse_args()

    notebooks = sorted(p for p in NOTEBOOK_DIR.glob("*.py") if is_marimo_notebook(p))
    if not notebooks:
        print("No marimo notebooks found in notebooks/ — nothing to check.")
        return 0

    stale: list[str] = []
    missing: list[str] = []

    for nb in notebooks:
        committed = nb.with_suffix(".ipynb")

        if args.fix:
            export_ipynb(nb, committed)
            print(f"regenerated {committed.relative_to(NOTEBOOK_DIR.parent)}")
            continue

        with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False) as tmp:
            fresh = Path(tmp.name)
        try:
            export_ipynb(nb, fresh)
            if not committed.exists():
                missing.append(committed.name)
            elif committed.read_bytes() != fresh.read_bytes():
                stale.append(committed.name)
            else:
                print(f"✅ {committed.name} in sync with {nb.name}")
        finally:
            fresh.unlink(missing_ok=True)

    if args.fix:
        return 0

    if missing or stale:
        print()
        for name in missing:
            print(f"❌ {name} is MISSING — export it from its marimo source.")
        for name in stale:
            print(f"❌ {name} is STALE — does not match `marimo export ipynb`.")
        print(
            "\nRegenerate with:\n"
            "    uv run python scripts/check_notebooks_synced.py --fix\n"
            "and commit the updated .ipynb files."
        )
        return 1

    print(f"\nAll {len(notebooks)} marimo notebook(s) have an up-to-date .ipynb.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
