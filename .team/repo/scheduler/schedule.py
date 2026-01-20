"""Schedule CSV management for Jules persona scheduling.

This module provides functions to read, write, and manage the schedule.csv
file that controls which persona runs next and tracks their PR outcomes.
"""

import csv
from pathlib import Path
from typing import Any

SCHEDULE_PATH = Path(".team/schedule.csv")
ORACLE_SCHEDULE_PATH = Path(".team/oracle_schedule.csv")
PERSONAS_DIR = Path(".team/personas")
FIELDNAMES = ["sequence", "persona", "session_id", "pr_number", "pr_status", "base_commit"]
ORACLE_FIELDNAMES = ["session_id", "created_at", "status"]
ORACLE_SESSION_MAX_AGE_HOURS = 24

# Personas that are excluded from automatic scheduling
# These exist in the personas directory but should not be scheduled automatically
EXCLUDED_PERSONAS = [
    "oracle",        # Runs on-demand, not in rotation
    "bdd_specialist", # Runs on-demand, not in rotation
    "franklin"       # Reserved for manual testing
]

# Fallback list if filesystem discovery fails
# This should match the actual personas in .team/personas/ (excluding EXCLUDED_PERSONAS)
FALLBACK_CYCLE_PERSONAS = [
    "absolutist", "artisan", "bolt", "builder", "curator", "docs_curator",
    "essentialist", "forge", "janitor", "lore", "maintainer", "organizer", "palette",
    "pruner", "refactor", "sapper", "scribe", "sentinel", "shepherd", "sheriff",
    "simplifier", "steward", "streamliner", "taskmaster", "typeguard",
    "visionary"
]


def discover_personas() -> list[str]:
    """Discover available personas from the filesystem.

    Returns a sorted list of persona names by scanning .team/personas/ directory,
    excluding personas in EXCLUDED_PERSONAS.

    Falls back to FALLBACK_CYCLE_PERSONAS if directory doesn't exist or is empty.
    """
    if not PERSONAS_DIR.exists():
        print(f"⚠️  Personas directory not found at {PERSONAS_DIR}, using fallback list")
        return FALLBACK_CYCLE_PERSONAS

    try:
        # Find all subdirectories (persona definitions)
        personas = [
            p.name for p in PERSONAS_DIR.iterdir()
            if p.is_dir() and not p.name.startswith('.') and p.name not in EXCLUDED_PERSONAS
        ]

        if not personas:
            print(f"⚠️  No personas found in {PERSONAS_DIR}, using fallback list")
            return FALLBACK_CYCLE_PERSONAS

        return sorted(personas)
    except Exception as e:
        print(f"⚠️  Error discovering personas: {e}, using fallback list")
        return FALLBACK_CYCLE_PERSONAS


def validate_persona_exists(persona: str) -> bool:
    """Check if a persona definition exists in the filesystem."""
    persona_path = PERSONAS_DIR / persona
    return persona_path.exists() and persona_path.is_dir()


def get_cycle_personas() -> list[str]:
    """Get the list of personas that should participate in scheduling.

    This is the main function to use when you need the persona rotation list.
    It automatically discovers personas from the filesystem.
    """
    return discover_personas()


# For backwards compatibility - use function instead of constant
CYCLE_PERSONAS = get_cycle_personas()


def load_schedule() -> list[dict[str, Any]]:
    """Load schedule.csv and return list of rows."""
    if not SCHEDULE_PATH.exists():
        return []
    
    with open(SCHEDULE_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_schedule(rows: list[dict[str, Any]]) -> None:
    """Save rows back to schedule.csv."""
    with open(SCHEDULE_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def get_current_sequence(rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, bool]:
    """Find the first row that needs work.

    Returns:
        Tuple of (current_row, schedule_modified)
        - current_row: First row that needs work, or None if all done
        - schedule_modified: True if rows were modified (invalid personas marked closed)

    Returns the first row where:
    - No session_id exists (not started yet)

    Skips rows with:
    - pr_status 'merged' or 'closed' (completed)
    - session_id exists (in progress - wait for PR tracking to update status)

    This prevents creating duplicate sessions for the same sequence when
    the PR is created/merged faster than the PR tracker updates the CSV.
    """
    modified = False

    for row in rows:
        session_id = row.get("session_id", "").strip()
        status = row.get("pr_status", "").strip().lower()

        # Skip completed rows
        if status in ["merged", "closed"]:
            continue

        # Skip rows that have a session (regardless of PR status)
        # Once a session exists, wait for PR tracker to update the status
        if session_id:
            continue

        # Skip excluded personas
        persona = row.get("persona", "").strip().lower()
        if persona in EXCLUDED_PERSONAS:
            continue

        # Skip personas that don't exist (auto-mark as closed)
        if not validate_persona_exists(persona):
            print(f"⚠️  Persona '{persona}' not found, marking sequence {row['sequence']} as closed")
            row['pr_status'] = 'closed'
            modified = True
            continue

        # This row needs work (no session exists yet)
        return row, modified

    return None, modified


def get_next_sequence(rows: list[dict[str, Any]], current: dict[str, Any]) -> dict[str, Any] | None:
    """Get the next sequence after the current one."""
    found_current = False
    for row in rows:
        if found_current:
            return row
        if row["sequence"] == current["sequence"]:
            found_current = True
    return None


def update_sequence(rows: list[dict[str, Any]], sequence: str, **updates: Any) -> list[dict[str, Any]]:
    """Update fields for a specific sequence."""
    for row in rows:
        if row["sequence"] == sequence:
            row.update(updates)
            break
    return rows


def count_remaining_empty(rows: list[dict[str, Any]]) -> int:
    """Count rows that haven't been started yet (no session_id)."""
    return sum(1 for row in rows if not row.get("session_id", "").strip())


def auto_extend(rows: list[dict[str, Any]], count: int = 50) -> list[dict[str, Any]]:
    """Add more rows to the schedule if running low.

    Uses round-robin through discovered personas, skipping any that don't exist.
    """
    cycle_personas = get_cycle_personas()

    if not cycle_personas:
        print("⚠️  No personas available for scheduling")
        return rows

    if not rows:
        last_seq = 0
        last_persona_idx = -1
    else:
        last_seq = int(rows[-1]["sequence"])
        last_persona = rows[-1]["persona"]
        try:
            last_persona_idx = cycle_personas.index(last_persona)
        except ValueError:
            last_persona_idx = -1

    added = 0
    for i in range(count):
        seq = last_seq + i + 1
        persona_idx = (last_persona_idx + i + 1) % len(cycle_personas)
        persona = cycle_personas[persona_idx]

        # Double-check persona exists before adding to schedule
        if not validate_persona_exists(persona):
            print(f"⚠️  Skipping non-existent persona '{persona}' during schedule extension")
            continue

        rows.append({
            "sequence": f"{seq:03d}",
            "persona": persona,
            "session_id": "",
            "pr_number": "",
            "pr_status": "",
            "base_commit": ""
        })
        added += 1

    if added < count:
        print(f"⚠️  Only added {added}/{count} sequences due to missing personas")

    return rows


def validate_and_fix(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate and fix schedule rows, returning fixed rows and list of issues found."""
    issues: list[str] = []
    fixed_rows: list[dict[str, Any]] = []
    
    seen_sequences = set()
    
    for i, row in enumerate(rows):
        # Ensure all required fields exist
        fixed_row = {field: row.get(field, "") for field in FIELDNAMES}
        
        # Fix sequence format
        seq = fixed_row["sequence"].strip()
        if not seq:
            issues.append(f"Row {i+1}: Missing sequence, auto-generating")
            seq = f"{len(fixed_rows)+1:03d}"
        elif not seq.isdigit():
            issues.append(f"Row {i+1}: Invalid sequence '{seq}', fixing")
            seq = f"{len(fixed_rows)+1:03d}"
        fixed_row["sequence"] = f"{int(seq):03d}"
        
        # Skip duplicate sequences
        if fixed_row["sequence"] in seen_sequences:
            issues.append(f"Row {i+1}: Duplicate sequence {fixed_row['sequence']}, skipping")
            continue
        seen_sequences.add(fixed_row["sequence"])
        
        # Validate persona
        persona = fixed_row["persona"].strip().lower()
        cycle_personas = get_cycle_personas()

        if persona:
            # Check if persona exists in filesystem
            if not validate_persona_exists(persona):
                issues.append(f"Row {i+1}: Persona '{persona}' not found in filesystem, marking as closed")
                fixed_row["pr_status"] = "closed"
            # Warn if persona is not in rotation (but exists in filesystem)
            elif persona not in cycle_personas and persona not in EXCLUDED_PERSONAS:
                issues.append(f"Row {i+1}: Persona '{persona}' exists but not in rotation")

        fixed_row["persona"] = persona
        
        # Normalize pr_status
        status = fixed_row["pr_status"].strip().lower()
        if status and status not in ["draft", "open", "merged", "closed"]:
            issues.append(f"Row {i+1}: Invalid pr_status '{status}', clearing")
            status = ""
        fixed_row["pr_status"] = status
        
        fixed_rows.append(fixed_row)
    
    # Sort by sequence
    fixed_rows.sort(key=lambda r: int(r["sequence"]))
    
    return fixed_rows, issues


# ============================================================================
# ORACLE SCHEDULE MANAGEMENT
# ============================================================================

def load_oracle_schedule() -> list[dict[str, Any]]:
    """Load oracle_schedule.csv and return list of rows."""
    if not ORACLE_SCHEDULE_PATH.exists():
        return []
    
    with open(ORACLE_SCHEDULE_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_oracle_schedule(rows: list[dict[str, Any]]) -> None:
    """Save rows back to oracle_schedule.csv."""
    with open(ORACLE_SCHEDULE_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ORACLE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def get_active_oracle_session() -> dict[str, Any] | None:
    """Get the current active Oracle session if it exists and is not expired.
    
    Returns the most recent Oracle session if:
    - It has a session_id
    - It was created less than ORACLE_SESSION_MAX_AGE_HOURS ago
    - Its status is 'active'
    
    Returns None if no valid session exists (need to create new one).
    """
    from datetime import datetime, timezone
    
    rows = load_oracle_schedule()
    if not rows:
        return None
    
    # Find the most recent active session
    for row in reversed(rows):
        session_id = row.get("session_id", "").strip()
        created_at = row.get("created_at", "").strip()
        status = row.get("status", "").strip().lower()
        
        if not session_id or status == "expired":
            continue
        
        # Check age
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
                
                if age_hours > ORACLE_SESSION_MAX_AGE_HOURS:
                    # Mark as expired and continue
                    row["status"] = "expired"
                    save_oracle_schedule(rows)
                    continue
                
                # Valid active session found
                return row
            except Exception:
                pass  # Invalid timestamp, skip
    
    return None


def register_oracle_session(session_id: str) -> None:
    """Register a new Oracle session in the schedule."""
    from datetime import datetime, timezone
    
    rows = load_oracle_schedule()
    
    # Add new row
    rows.append({
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    })
    
    save_oracle_schedule(rows)


def sync_session_states_from_api() -> None:
    """Sync session states from Jules API to schedule.csv.

    This checks all sessions with session_ids in the schedule and updates
    their states if they've changed (e.g., IN_PROGRESS -> COMPLETED).
    """
    from repo.core.client import TeamClient

    rows = load_schedule()
    client = TeamClient()

    updated = 0
    for row in rows:
        session_id = row.get("session_id", "").strip()
        if not session_id:
            continue

        try:
            session = client.get_session(session_id)
            api_state = session.get("state", "UNKNOWN")

            # Map Jules API states to our pr_status convention
            # Note: This is informational only - PR status is still authoritative
            # We could add a "session_state" column if needed
            print(f"  Session {session_id[:8]}: {api_state}")
        except Exception as e:
            print(f"  ⚠️ Failed to get session {session_id[:8]}: {e}")


def extract_sequence_from_title(title: str) -> str | None:
    """Extract sequence number from session title.

    Matches pattern: "{seq} {emoji} {persona} {repo}"
    Example: "002 🎨 artisan egregora"

    Returns sequence as string (e.g., "002") or None if not found.
    """
    import re
    # Match 3-digit sequence at the start of title
    match = re.match(r'^(\d{3})\s', title)
    return match.group(1) if match else None


def list_recent_sessions(limit: int = 20) -> None:
    """List recent sessions with schedule context.

    Shows:
    - Session ID
    - Sequence number (from schedule or parsed from title)
    - Persona
    - State
    - Base commit (if tracked)
    - PR number (if exists)
    """
    from repo.core.client import TeamClient

    rows = load_schedule()
    client = TeamClient()

    # Build lookup from session_id to schedule row
    session_lookup = {row.get("session_id", ""): row for row in rows if row.get("session_id", "")}

    try:
        sessions_data = client.list_sessions()
        sessions = sessions_data.get("sessions", [])

        print(f"\n{'Seq':<5} {'Session ID':<10} {'Persona':<15} {'State':<15} {'Base':<8} {'PR':<5}")
        print("-" * 70)

        for session in sessions[:limit]:
            session_full_id = session.get("name", "")
            session_id = session_full_id.split("/")[-1] if "/" in session_full_id else session_full_id
            session_short = session_id[:8] if session_id else "N/A"
            state = session.get("state", "UNKNOWN")
            title = session.get("title", "")

            # Try to extract persona from title
            persona = "N/A"
            cycle_personas = get_cycle_personas()
            for pid in cycle_personas + EXCLUDED_PERSONAS:
                if pid in title.lower():
                    persona = pid
                    break

            # Check if in schedule
            schedule_row = session_lookup.get(session_id)
            if schedule_row:
                seq = schedule_row.get("sequence", "N/A")
                persona = schedule_row.get("persona", persona)
                base_commit = schedule_row.get("base_commit", "N/A")
                pr_number = schedule_row.get("pr_number", "N/A")
            else:
                # Not in schedule - try to parse sequence from title
                seq = extract_sequence_from_title(title) or "N/A"
                base_commit = "N/A"
                pr_number = "N/A"

            print(f"{seq:<5} {session_short:<10} {persona:<15} {state:<15} {base_commit:<8} {pr_number:<5}")

    except Exception as e:
        print(f"❌ Failed to list sessions: {e}")


def health_check() -> None:
    """Perform a health check on persona configuration and schedule consistency.

    Checks:
    1. Persona directory exists and is readable
    2. All personas in schedule have definitions
    3. All persona definitions are in the cycle or excluded list
    4. Schedule entries for missing personas are marked closed
    """
    print("🔍 Persona Health Check\n")

    # Check 1: Persona directory
    print(f"1. Checking persona directory: {PERSONAS_DIR}")
    if not PERSONAS_DIR.exists():
        print(f"   ❌ Directory not found!")
        return
    print(f"   ✅ Directory exists\n")

    # Check 2: Discover personas
    print("2. Discovering available personas...")
    discovered = discover_personas()
    print(f"   ✅ Found {len(discovered)} personas: {', '.join(discovered[:5])}...")
    if len(discovered) > 5:
        print(f"      (and {len(discovered) - 5} more)\n")
    else:
        print()

    # Check 3: Excluded personas
    print("3. Checking excluded personas...")
    for persona in EXCLUDED_PERSONAS:
        exists = validate_persona_exists(persona)
        status = "✅" if exists else "⚠️ "
        print(f"   {status} {persona}: {'exists' if exists else 'not found'}")
    print()

    # Check 4: Schedule consistency
    print("4. Checking schedule.csv consistency...")
    if not SCHEDULE_PATH.exists():
        print("   ⚠️  schedule.csv not found")
        return

    rows = load_schedule()
    print(f"   📊 Total schedule entries: {len(rows)}\n")

    # Count by status
    by_status = {}
    missing_personas = []
    for row in rows:
        persona = row.get("persona", "").strip()
        status = row.get("pr_status", "").strip() or "pending"
        by_status[status] = by_status.get(status, 0) + 1

        # Check if persona exists
        if persona and not validate_persona_exists(persona):
            missing_personas.append((row.get("sequence", "?"), persona, status))

    print("   Status breakdown:")
    for status, count in sorted(by_status.items()):
        print(f"      {status}: {count}")
    print()

    # Report missing personas
    if missing_personas:
        print(f"   ⚠️  Found {len(missing_personas)} entries with missing persona definitions:")
        for seq, persona, status in missing_personas[:10]:
            print(f"      Seq {seq}: {persona} (status: {status or 'pending'})")
        if len(missing_personas) > 10:
            print(f"      ... and {len(missing_personas) - 10} more")
        print()
        print("   💡 Run with --fix to automatically mark these as closed")
    else:
        print("   ✅ All schedule entries reference valid personas")

    print("\n✨ Health check complete!")


def main() -> None:
    """CLI entry point for schedule management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage Jules schedule.csv")
    parser.add_argument("--fix", action="store_true", help="Validate and fix the schedule")
    parser.add_argument("--extend", type=int, help="Add N more rows to the schedule")
    parser.add_argument("--show", action="store_true", help="Show current schedule status")
    parser.add_argument("--list-sessions", action="store_true", help="List recent sessions from Jules API")
    parser.add_argument("--sync-states", action="store_true", help="Sync session states from Jules API")
    parser.add_argument("--health", action="store_true", help="Run health check on persona configuration")
    args = parser.parse_args()
    
    rows = load_schedule()
    
    if args.fix:
        rows, issues = validate_and_fix(rows)
        if issues:
            print("Fixed issues:")
            for issue in issues:
                print(f"  - {issue}")
        save_schedule(rows)
        print(f"Schedule validated and saved ({len(rows)} rows)")
    
    if args.extend:
        rows = auto_extend(rows, args.extend)
        save_schedule(rows)
        print(f"Extended schedule by {args.extend} rows (now {len(rows)} total)")
    
    if args.show:
        current, _ = get_current_sequence(rows)
        remaining = count_remaining_empty(rows)
        print(f"Schedule: {len(rows)} total rows, {remaining} not started")
        if current:
            print(f"Current: [{current['sequence']}] {current['persona']} - {current['pr_status'] or 'not started'}")

    if args.list_sessions:
        list_recent_sessions()

    if args.sync_states:
        print("Syncing session states from Jules API...")
        sync_session_states_from_api()

    if args.health:
        health_check()


if __name__ == "__main__":
    main()
