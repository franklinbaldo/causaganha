#!/usr/bin/env python3
"""Dashboard Live-Status Verifier for CausaGanha."""

import argparse
import json
import os
import re
import sys
from typing import Any


def extract_with_playwright(url: str, screenshot_path: str | None = None) -> tuple[bool, str]:
    """Attempt to extract text content using Playwright.
    Returns (success, text_content)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed, skipping browser layer.")
        return False, ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            print(f"Loading {url} via Playwright...")
            page.goto(url, wait_until="networkidle", timeout=30000)

            try:
                page.wait_for_selector("text=CausaGanha", timeout=10000)
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Timeout waiting for elements: {e}")

            if screenshot_path:
                os.makedirs(os.path.dirname(os.path.abspath(screenshot_path)), exist_ok=True)
                page.screenshot(path=screenshot_path)
                print(f"Captured screenshot to {screenshot_path}")

            # Extract full text
            text_content = page.evaluate("document.body.innerText")
            browser.close()
            return True, text_content
    except Exception as e:
        print(f"Playwright extraction failed: {e}")
        return False, ""

def extract_with_urllib(url: str) -> tuple[bool, str]:
    """Fallback extraction using built-in urllib.
    Returns (success, text_content)
    """
    import urllib.request
    try:
        print(f"Loading {url} via urllib fallback...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15.0) as response:
            html_content = response.read().decode("utf-8", errors="replace")

        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_content, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("&nbsp;", " ")
        text = re.sub(r"\s+", " ", text).strip()

        return True, text
    except Exception as e:
        print(f"urllib extraction failed: {e}")
        return False, ""

def parse_dashboard_signals(text: str) -> dict[str, Any]:
    """Parses the dashboard text to extract key operational signals.
    """
    signals = {
        "healthy_tribunals": "unknown",
        "total_tribunals": "unknown",
        "last_collection": "unknown",
        "global_eta": "unknown",
        "pending_cards_count": 0,
        "overall_state": "unknown"
    }

    # "0 of 91 tribunais saudáveis"
    healthy_match = re.search(r"(\d+)\s+of\s+(\d+)\s+tribunais saudáveis", text, re.IGNORECASE)
    if healthy_match:
        signals["healthy_tribunals"] = healthy_match.group(1)
        signals["total_tribunals"] = healthy_match.group(2)

    # "última coleta: --:--"
    coleta_match = re.search(r"última coleta:\s*([^\s\|]+)", text, re.IGNORECASE)
    if coleta_match:
        signals["last_collection"] = coleta_match.group(1)

    # "Global ETA: Pending" or "Global ETA: 12 days"
    eta_match = re.search(r"Global ETA:\s*([A-Za-z0-9\s]+)", text, re.IGNORECASE)
    if eta_match:
        # Strip trailing newlines or extra text if any, limit length
        val = eta_match.group(1).strip()
        if "Global Archiving" in val:
            val = val.split("Global")[0].strip()
        signals["global_eta"] = val

    # Count occurrences of "Status PENDING" or "STATUS\nPENDING"
    # To handle both single line (fallback) and newline (playwright) representations
    pending_count = len(re.findall(r"status\s*pending", text, re.IGNORECASE))
    signals["pending_cards_count"] = pending_count

    # Determine overall state
    if signals["last_collection"] == "--:--" or "pending" in str(signals["global_eta"]).lower() or (pending_count > 0 and signals["healthy_tribunals"] == "0"):
        signals["overall_state"] = "Stalled / Pending"
    else:
        signals["overall_state"] = "Alive and Advancing"

    return signals

def main():
    parser = argparse.ArgumentParser(description="Verify CausaGanha Dashboard Status")
    parser.add_argument("--url", default="https://franklinbaldo.github.io/causaganha/", help="Dashboard URL")
    parser.add_argument("--screenshot-path", default="verification/live_dashboard_status.png", help="Path to save the screenshot if using browser")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    layer = "none"
    content = ""
    success = False

    # Try browser first
    success, content = extract_with_playwright(args.url, args.screenshot_path)
    if success:
        layer = "browser"
    else:
        # Fallback to urllib
        success, content = extract_with_urllib(args.url)
        if success:
            layer = "urllib"

    if not success:
        print("Failed to fetch dashboard via all available layers.", file=sys.stderr)
        sys.exit(1)

    signals = parse_dashboard_signals(content)

    result = {
        "target": args.url,
        "extraction_layer": layer,
        "signals": signals
    }

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("=== Dashboard Verification Report ===")
        print(f"Target: {args.url}")
        print(f"Extraction Layer: {layer}")
        print(f"Overall State: {signals['overall_state']}")
        print(f"Healthy Tribunals: {signals['healthy_tribunals']} / {signals['total_tribunals']}")
        print(f"Last Collection: {signals['last_collection']}")
        print(f"Global ETA: {signals['global_eta']}")
        print(f"Pending Cards Found: {signals['pending_cards_count']}")

if __name__ == "__main__":
    main()
