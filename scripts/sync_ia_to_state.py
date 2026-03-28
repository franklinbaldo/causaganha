#!/usr/bin/env python3
"""Sync Internet Archive metadata to data/state.json for dashboard visibility."""

import json
import httpx
from pathlib import Path
from datetime import date
import structlog

log = structlog.get_logger()

STATE_FILE = Path("/home/franklin/workspace/causaganha/data/state.json")
QUERY = "collection:(causaganha-archive) OR identifier:(djen-*)"
IA_SEARCH_URL = "https://archive.org/advancedsearch.php"

def parse_identifier(identifier, title):
    """Extract date and tribunal from IA identifier or title.
    
    Examples:
    - djen-pjecor-2025 -> Tribunal: PJECOR, Year: 2025 (Needs more date info from metadata/title)
    - djen-stj-2026 -> Tribunal: STJ, Year: 2026
    - djen-1990-06-19 -> Date: 1990-06-19 (Generic, might need tribunal from title)
    """
    # Attempt to extract from title if it looks like "DJEN Data - YYYY-MM-DD"
    if "DJEN Data - " in title:
        try:
            date_str = title.split(" - ")[1].strip()
            # Simple heuristic for tribunal: many generic ones are actually consolidated or main
            # But recent ones have tribunal in identifier: djen-stj-2026
            parts = identifier.split("-")
            if len(parts) >= 2:
                # Handle cases like djen-raw-2026-01-23-TJSP
                if parts[1].lower() == "raw" and len(parts) >= 6:
                    tribunal = parts[5].upper()
                    date_str = f"{parts[2]}-{parts[3]}-{parts[4]}"
                    return date_str, tribunal
                # Case djen-stj-2026
                tribunal = parts[1].upper()
                if tribunal not in {"STJ", "STF", "TST", "TSE", "STM", "CNJ", "CJF", "PJECOR"}:
                    # Try next parts
                    if len(parts) >= 3:
                        tribunal = parts[2].upper()
                return date_str, tribunal
        except Exception:
            pass
            
    # Fallback for detailed identifiers
    # djen-raw-2026-01-23-TJSP
    parts = identifier.split("-")
    if "raw" in parts and len(parts) >= 6:
        try:
            date_str = f"{parts[2]}-{parts[3]}-{parts[4]}"
            tribunal = parts[5].upper()
            return date_str, tribunal
        except Exception:
            pass

    return None, None

def main():
    log.info("sync_ia_starting", query=QUERY)
    
    params = {
        "q": QUERY,
        "fl[]": ["identifier", "title", "date", "description"],
        "rows": 10000,
        "output": "json"
    }
    
    response = httpx.get(IA_SEARCH_URL, params=params, timeout=60)
    if response.status_code != 200:
        log.error("ia_search_failed", status=response.status_code)
        return

    data = response.json()
    docs = data.get("response", {}).get("docs", [])
    log.info("ia_search_complete", found=len(docs))

    # Load existing state
    state = {"version": 2, "entries": {}}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except Exception:
            pass

    entries = state.get("entries", {})
    count_new = 0

    for doc in docs:
        identifier = doc.get("identifier", "")
        title = doc.get("title", "")
        
        # log.debug("processing_item", id=identifier, title=title)
        date_str, tribunal = parse_identifier(identifier, title)
        
        if date_str and tribunal:
            if date_str not in entries:
                entries[date_str] = {}
            
            # Use status 'uploaded' to match backfill code
            if entries[date_str].get(tribunal) != "uploaded":
                entries[date_str][tribunal] = "uploaded"
                count_new += 1
                # log.debug("mapped_hit", date=date_str, tribunal=tribunal)

    # Save back
    state["entries"] = entries
    state["updated_at"] = date.today().isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))
    
    log.info("sync_ia_finalized", total_hits_found=len(docs), new_successful_mappings=count_new, total_recorded=len(entries))

    # --- AUTOMATIC DASHBOARD UPDATE ---
    try:
        import sys
        import os
        repo_root = "/home/franklin/workspace/causaganha"
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
            
        from scripts.dashboard.generate_data import generate_dashboard_data
        db_path = Path(f"{repo_root}/data/causaganha.duckdb")
        output_path = Path(f"{repo_root}/dashboard/public/dashboard-data.json")
        log.info("dashboard_update_starting")
        generate_dashboard_data(db_path, output_path)
        log.info("dashboard_update_complete")
    except Exception as e:
        log.error("dashboard_update_failed", error=str(e))

if __name__ == "__main__":
    main()
