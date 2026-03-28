#!/usr/bin/env python3
"""Browserless public dashboard status verification."""

import json
import logging
import re
import urllib.request
from typing import Any


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DASHBOARD_URL = "https://franklinbaldo.github.io/causaganha/"


def fetch_html(url: str = DASHBOARD_URL) -> str | None:
    """Fetch dashboard HTML."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=10) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except Exception as e:
        logger.exception("Failed to fetch %s: %s", url, e)
        return None


def analyze_html(html: str | None) -> dict[str, Any]:
    """Analyze the given HTML content and return status summary."""
    if not html:
        return {
            "status": "fetch_failed",
            "layer": "browserless text fetch",
            "title": None,
            "healthy_tribunals": 0,
            "total_tribunals": 0,
            "last_collection": None,
            "global_eta": None,
            "zips_synced_done": 0,
            "zips_synced_total": 0,
        }

    # Extract title
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "Unknown"

    # Extract healthy tribunals count
    healthy_match = re.search(r"(\d+)\s+of\s+(\d+)\s+tribunais saudáveis", html)
    healthy = int(healthy_match.group(1)) if healthy_match else 0
    total_tribs = int(healthy_match.group(2)) if healthy_match else 91

    # Extract last collection time
    collection_match = re.search(r"última coleta:\s*([0-9:]+|--:--)", html)
    last_collection = collection_match.group(1) if collection_match else "--:--"

    # Extract global ETA
    eta_match = re.search(r"Global ETA:\s*([^<]+)", html)
    global_eta = eta_match.group(1).strip() if eta_match else "Pending"

    # Extract ZIPs Synced (from fallback structure like test_healthy_fallback.html)
    zips_synced_done = 0
    zips_synced_total = 0
    zips_match = re.search(r"ZIPs Synchronized.*?>(\d+)\s*/\s*(\d+)<", html, re.DOTALL | re.IGNORECASE)
    if zips_match:
        zips_synced_done = int(zips_match.group(1))
        zips_synced_total = int(zips_match.group(2))

    # Determine Status
    if healthy == 0 and last_collection == "--:--" and global_eta == "Pending":
        status = "alive_but_stale_looking"
    elif healthy > 0 or last_collection != "--:--" or global_eta != "Pending":
        status = "advancing"
    else:
        status = "alive"

    return {
        "status": status,
        "layer": "browserless text fetch",
        "title": title,
        "healthy_tribunals": healthy,
        "total_tribunals": total_tribs,
        "last_collection": last_collection,
        "global_eta": global_eta,
        "zips_synced_done": zips_synced_done,
        "zips_synced_total": zips_synced_total,
    }


if __name__ == "__main__":
    import sys
    html = fetch_html()
    if html:
        sys.stdout.write(json.dumps(analyze_html(html), indent=2) + "\n")
    else:
        sys.stdout.write(json.dumps(analyze_html(None), indent=2) + "\n")
