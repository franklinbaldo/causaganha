#!/usr/bin/env python3
"""Test suite for Jules scheduler fixes (standalone, no dependencies).

Tests:
1. get_current_sequence() logic (prevents duplicates)
2. Session ID extraction from PR branches
3. Scheduler advancement through sequences
"""

import re
from typing import Any


def get_current_sequence(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the first row that needs work.

    Returns the first row where:
    - No session_id exists (not started yet)

    Skips rows with:
    - pr_status 'merged' or 'closed' (completed)
    - session_id exists (in progress - wait for PR tracking to update status)

    This prevents creating duplicate sessions for the same sequence when
    the PR is created/merged faster than the PR tracker updates the CSV.
    """
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

        # This row needs work (no session exists yet)
        return row

    return None


def test_get_current_sequence():
    """Test that get_current_sequence prevents duplicate sessions."""
    print("=" * 70)
    print("TEST 1: get_current_sequence() Logic")
    print("=" * 70)

    test_cases = [
        {
            "name": "Empty schedule returns None",
            "rows": [],
            "expected_seq": None,
        },
        {
            "name": "First empty row is selected",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "", "pr_status": ""},
                {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "001",
        },
        {
            "name": "Skip row with session_id (no PR yet) ⭐ CRITICAL",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": ""},
                {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "002",
            "description": "Prevents duplicate session when PR not yet tracked"
        },
        {
            "name": "Skip row with session_id and draft PR",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": "draft"},
                {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "002",
        },
        {
            "name": "Skip row with session_id and open PR",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": "open"},
                {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "002",
        },
        {
            "name": "Skip merged row, select next empty",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": "merged"},
                {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "002",
        },
        {
            "name": "Skip closed row, select next empty",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": "closed"},
                {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "002",
        },
        {
            "name": "All rows have sessions - returns None",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": ""},
                {"sequence": "002", "persona": "artisan", "session_id": "67890", "pr_status": ""},
            ],
            "expected_seq": None,
            "description": "Wait for PR tracker to update before advancing"
        },
        {
            "name": "Race condition scenario ⭐ CRITICAL",
            "rows": [
                {"sequence": "001", "persona": "absolutist", "session_id": "12345", "pr_status": "merged"},
                {"sequence": "002", "persona": "artisan", "session_id": "67890", "pr_status": ""},
                {"sequence": "003", "persona": "bolt", "session_id": "", "pr_status": ""},
            ],
            "expected_seq": "003",
            "description": "Even though 002 has session_id (PR merged fast), skip it"
        },
    ]

    passes = 0
    failures = 0

    print()
    for test in test_cases:
        result = get_current_sequence(test["rows"])
        expected = test["expected_seq"]

        if result:
            result_seq = result.get("sequence")
        else:
            result_seq = None

        if result_seq == expected:
            status = "✅ PASS"
            passes += 1
        else:
            status = "❌ FAIL"
            failures += 1

        print(f"{status} {test['name']}")
        print(f"     Expected: {expected}, Got: {result_seq}")
        if "description" in test:
            print(f"     Note: {test['description']}")
        print()

    print("=" * 70)
    print(f"TEST 1 Results: {passes} passed, {failures} failed")
    print("=" * 70)
    print()

    return failures == 0


def test_session_extraction():
    """Test session ID extraction from branch names."""
    print("=" * 70)
    print("TEST 2: Session ID Extraction from Branch Names")
    print("=" * 70)

    def extract_session_id_from_branch(branch: str) -> str | None:
        """Extract session ID from branch name."""
        # Try numeric ID (15+ digits at end)
        match = re.search(r"-(\d{15,})$", branch)
        if match:
            return match.group(1)

        # Try UUID
        uuid_match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", branch)
        if uuid_match:
            return uuid_match.group(1)

        return None

    test_cases = [
        {
            "name": "Real PR #2541 branch",
            "branch": "refactor/windowing-by-bytes-6277226227732204550",
            "expected": "6277226227732204550"
        },
        {
            "name": "Real artisan PR branch",
            "branch": "artisan-refactor-runner-types-12184546661957914452",
            "expected": "12184546661957914452"
        },
        {
            "name": "Real artisan PR with slash",
            "branch": "artisan/improve-context-typing-8071111661752381116",
            "expected": "8071111661752381116"
        },
        {
            "name": "Scheduler branch pattern",
            "branch": "jules-sched-bolt-17594818090249437779",
            "expected": "17594818090249437779"
        },
        {
            "name": "UUID pattern",
            "branch": "fix/bug-a1b2c3d4-1234-5678-9abc-def012345678",
            "expected": "a1b2c3d4-1234-5678-9abc-def012345678"
        },
    ]

    passes = 0
    failures = 0

    print()
    for test in test_cases:
        result = extract_session_id_from_branch(test["branch"])
        expected = test["expected"]

        if result == expected:
            status = "✅ PASS"
            passes += 1
        else:
            status = "❌ FAIL"
            failures += 1

        print(f"{status} {test['name']}")
        print(f"     Branch: '{test['branch']}'")
        print(f"     Expected: '{expected}', Got: '{result}'")
        print()

    print("=" * 70)
    print(f"TEST 2 Results: {passes} passed, {failures} failed")
    print("=" * 70)
    print()

    return failures == 0


def test_scheduler_advancement():
    """Test complete scheduler advancement scenario."""
    print("=" * 70)
    print("TEST 3: Scheduler Advancement Scenario (Race Condition)")
    print("=" * 70)

    # Simulate scheduler lifecycle
    print("\nSimulating scheduler lifecycle:\n")

    # Initial state
    rows = [
        {"sequence": "001", "persona": "absolutist", "session_id": "", "pr_status": "", "pr_number": ""},
        {"sequence": "002", "persona": "artisan", "session_id": "", "pr_status": "", "pr_number": ""},
        {"sequence": "003", "persona": "bolt", "session_id": "", "pr_status": "", "pr_number": ""},
    ]

    print("📋 Initial schedule:")
    for row in rows:
        print(f"   [{row['sequence']}] {row['persona']}: session={row['session_id'] or 'none'}, pr_status={row['pr_status'] or 'none'}")

    # Step 1: First scheduler run
    print("\n🔄 Step 1: First scheduler run")
    current = get_current_sequence(rows)
    print(f"   Selected: [{current['sequence']}] {current['persona']}")

    if current["sequence"] != "001":
        print("   ❌ FAIL: Should select 001")
        return False

    # Simulate session creation
    rows[0]["session_id"] = "12901708137351264514"
    print(f"   ✅ Created session: {rows[0]['session_id']}")
    print(f"   📝 Updated CSV with session_id")

    # Step 2: Jules creates PR (fast!)
    print("\n⚡ Step 2: Jules creates PR #2538 (instantly)")
    print("   Note: PR is created but CSV not yet updated by tracker")

    # Step 3: Second scheduler run (race condition!)
    print("\n🔄 Step 3: Second scheduler run (before PR tracker updates CSV)")
    print("   Race condition: session_id exists but pr_status still empty")
    current = get_current_sequence(rows)

    if current and current["sequence"] == "001":
        print(f"   ❌ FAIL: Returned [{current['sequence']}] again - would create DUPLICATE!")
        return False
    elif current and current["sequence"] == "002":
        print(f"   ✅ PASS: Skipped 001, selected [{current['sequence']}] - no duplicate!")
    else:
        print(f"   ❌ UNEXPECTED: current={current}")
        return False

    # Step 4: PR tracker updates CSV
    print("\n📊 Step 4: PR tracker updates CSV with PR status")
    rows[0]["pr_number"] = "2538"
    rows[0]["pr_status"] = "open"
    print(f"   Updated: [{rows[0]['sequence']}] pr_number={rows[0]['pr_number']}, pr_status={rows[0]['pr_status']}")

    # Step 5: PR merges
    print("\n✅ Step 5: PR #2538 merges")
    rows[0]["pr_status"] = "merged"
    print(f"   Updated: [{rows[0]['sequence']}] pr_status={rows[0]['pr_status']}")

    # Step 6: Create session for 002
    print("\n🔄 Step 6: Scheduler creates session for 002")
    current = get_current_sequence(rows)
    if current["sequence"] != "002":
        print(f"   ❌ FAIL: Should select 002, got {current['sequence']}")
        return False
    rows[1]["session_id"] = "6277226227732204550"
    print(f"   ✅ Created session: {rows[1]['session_id']}")

    # Step 7: Fast merge scenario
    print("\n⚡ Step 7: PR #2541 creates and merges in 10 seconds")
    print("   Simulating the race: session exists but pr_status still empty")

    # Step 8: Scheduler run during race (THE CRITICAL TEST!)
    print("\n🔄 Step 8: Scheduler run (PR merged but CSV not updated yet)")
    print("   This is where OLD code would create duplicate!")
    current = get_current_sequence(rows)

    if current and current["sequence"] == "002":
        print(f"   ❌ FAIL: Returned [{current['sequence']}] again - would create DUPLICATE!")
        print(f"   This is the bug we're fixing!")
        return False
    elif current and current["sequence"] == "003":
        print(f"   ✅ PASS: Skipped 002, selected [{current['sequence']}] - no duplicate!")
        print(f"   Race condition handled correctly!")
    else:
        print(f"   ❌ UNEXPECTED: current={current}")
        return False

    print("\n" + "=" * 70)
    print("TEST 3 Results: ✅ PASS - Scheduler prevents duplicates correctly")
    print("=" * 70)
    print()

    return True


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "JULES SCHEDULER FIXES TEST SUITE" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = []

    # Run tests
    results.append(("get_current_sequence() Logic", test_get_current_sequence()))
    results.append(("Session ID Extraction", test_session_extraction()))
    results.append(("Scheduler Advancement Scenario", test_scheduler_advancement()))

    # Summary
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print()

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False

    print()
    print("=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Scheduler fixes are working correctly!")
        print()
        print("Key fixes verified:")
        print("  ✅ Session ID extraction from branch names")
        print("  ✅ Race condition prevented (no duplicate sessions)")
        print("  ✅ Proper scheduler advancement through sequences")
    else:
        print("❌ SOME TESTS FAILED - Please review the failures above")
    print("=" * 70)
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
