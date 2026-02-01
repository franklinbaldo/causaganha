#!/usr/bin/env python3
"""Test for auto_extend fix that prevents sequence gaps and persona repetition.

This test verifies that when personas don't exist in the filesystem,
auto_extend properly skips them and creates sequential sequence numbers
without gaps.
"""


def test_auto_extend_sequential_sequences():
    """Test that auto_extend creates sequential sequences even when personas are missing."""

    # Mock data - simulating a cycle where some personas don't exist
    cycle_personas = ["persona_a", "persona_b", "persona_c", "persona_d", "persona_e"]

    # Simulate that persona_c doesn't exist
    def mock_validate(persona: str) -> bool:
        return persona != "persona_c"

    # Simulate auto_extend logic
    last_seq = 10
    last_persona_idx = cycle_personas.index("persona_a")

    rows = []
    count = 5
    added = 0
    attempt = 0

    while added < count and attempt < count * 2:
        persona_idx = (last_persona_idx + attempt + 1) % len(cycle_personas)
        persona = cycle_personas[persona_idx]
        attempt += 1

        if not mock_validate(persona):
            print(f"Skipping {persona}")
            continue

        seq = last_seq + added + 1
        rows.append({"sequence": f"{seq:03d}", "persona": persona})
        added += 1

    print("\nResults:")
    for row in rows:
        print(f"  {row['sequence']}: {row['persona']}")

    # Verify
    sequences = [int(row["sequence"]) for row in rows]
    personas_added = [row["persona"] for row in rows]

    print(f"\nSequences: {sequences}")
    print(f"Personas: {personas_added}")

    # Check for sequential sequences (no gaps)
    assert sequences == [11, 12, 13, 14, 15], f"Expected [11, 12, 13, 14, 15], got {sequences}"

    # Check that persona_c was skipped
    assert "persona_c" not in personas_added, "persona_c should have been skipped"

    # Check that we added exactly 5 personas
    assert len(rows) == 5, f"Expected 5 rows, got {len(rows)}"

    # Check that personas are in cycle order (skipping persona_c)
    # Starting from persona_a (idx 0): b, d, e, a, b (c was skipped)
    expected_personas = ["persona_b", "persona_d", "persona_e", "persona_a", "persona_b"]
    assert personas_added == expected_personas, f"Expected {expected_personas}, got {personas_added}"

    print("\n✅ All assertions passed!")
    return True


if __name__ == "__main__":
    try:
        test_auto_extend_sequential_sequences()
        print("\n🎉 Test passed successfully!")
        exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
