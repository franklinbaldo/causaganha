#!/usr/bin/env python3
"""
Extract <style> blocks from all .astro/.svelte files and move them to index.css.

Usage: python scripts/extract_local_css.py [--dry-run]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

WEB_SRC = Path(__file__).parent.parent / "web" / "src"
INDEX_CSS = WEB_SRC / "index.css"

# Matches <style> or <style lang="ts"> etc. but NOT <style is:global>
STYLE_RE = re.compile(
    r'\n?<style(?![^>]*\bis:global\b)[^>]*>(.*?)</style>',
    re.DOTALL,
)


def extract_and_strip(path: Path) -> str | None:
    """Return extracted CSS block content, or None if no local style found."""
    src = path.read_text()
    match = STYLE_RE.search(src)
    if not match:
        return None
    return match.group(1)


def strip_style_block(path: Path) -> None:
    src = path.read_text()
    new_src = STYLE_RE.sub("", src).rstrip() + "\n"
    if not DRY_RUN:
        path.write_text(new_src)


def relative(path: Path) -> str:
    return str(path.relative_to(WEB_SRC.parent.parent))


def main() -> None:
    files = sorted(
        [*WEB_SRC.rglob("*.astro"), *WEB_SRC.rglob("*.svelte")]
    )

    extracted: list[tuple[Path, str]] = []
    for f in files:
        css = extract_and_strip(f)
        if css and css.strip():
            extracted.append((f, css))

    if not extracted:
        print("No local <style> blocks found.")
        return

    print(f"Found {len(extracted)} files with local CSS:")
    for f, _ in extracted:
        print(f"  {relative(f)}")

    # Build the appendix
    sections: list[str] = ["\n\n/* ═══════════════════════════════════════════\n"
                            "   Component & Page Styles (extracted from source)\n"
                            "   ═══════════════════════════════════════════ */\n"]
    for f, css in extracted:
        label = relative(f)
        sections.append(f"\n/* ── {label} ── */\n{css.strip()}\n")

    appendix = "\n".join(sections)

    if DRY_RUN:
        print("\n--- DRY RUN: would append to index.css ---")
        print(appendix[:2000], "..." if len(appendix) > 2000 else "")
        print(f"\nTotal characters to append: {len(appendix)}")
    else:
        with INDEX_CSS.open("a") as fh:
            fh.write(appendix)
        print(f"\nAppended to {relative(INDEX_CSS)}")

        # Strip style blocks from source files
        for f, _ in extracted:
            strip_style_block(f)
            print(f"  Stripped: {relative(f)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
