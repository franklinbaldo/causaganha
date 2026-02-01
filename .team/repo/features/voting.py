import csv
from pathlib import Path
from typing import Dict, List, Optional
import datetime

VOTES_FILE = Path(".team/votes.csv")
SCHEDULE_FILE = Path(".team/schedule.csv")
PERSONAS_ROOT = Path(".team/personas")

class VoteManager:
    def __init__(self, schedule_file: Path = SCHEDULE_FILE, votes_file: Path = VOTES_FILE):
        self.schedule_file = schedule_file
        self.votes_file = votes_file

    def cast_vote(self, voter_sequence: str, candidate_personas: List[str]) -> None:
        """
        Cast ranked votes for personas.

        NEW MODEL: Votes are NOT cast for a specific sequence.
        Instead, for any target sequence, we tally the last N votes
        (where N = roster size) from the most recent voters.

        Format: [voter_sequence, candidates] (no sequence_cast column)

        If a vote already exists for this voter_sequence, it is OVERWRITTEN.
        """
        # Store candidates as comma-separated array
        candidates_array = ",".join(candidate_personas)

        # Read existing votes, filter out any from same voter_sequence
        existing_votes = []
        if self.votes_file.exists():
            with open(self.votes_file, mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Keep votes from OTHER voter sequences
                    if row['voter_sequence'] != voter_sequence:
                        existing_votes.append(row)

        # Write all votes back, with new vote added
        with open(self.votes_file, mode='w', newline='') as f:
            fieldnames = ['voter_sequence', 'candidates']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_votes)
            writer.writerow({
                'voter_sequence': voter_sequence,
                'candidates': candidates_array
            })

    def _get_roster_size(self) -> int:
        """Count active persona directories."""
        if not PERSONAS_ROOT.exists():
            return 0
        return len([d for d in PERSONAS_ROOT.iterdir() if d.is_dir()])

    def _is_sequence_executed(self, sequence_id: str) -> bool:
        """Check if a sequence in schedule.csv has a session_id or pr_status."""
        if not self.schedule_file.exists():
            return False

        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['sequence'] == sequence_id:
                    return bool(row.get('session_id') or row.get('pr_status'))
        return False

    def get_next_open_sequence(self) -> Optional[str]:
        """
        Find the next sequence that has no session_id (not yet executed).
        This is the sequence we should apply votes to.
        """
        if not self.schedule_file.exists():
            return None

        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('session_id') and not row.get('pr_status'):
                    return row['sequence']
        return None

    def get_tally(self, target_sequence: str) -> Dict[str, int]:
        """
        Tally votes for a target sequence using ROLLING WINDOW.

        NEW MODEL: We use the last N votes (where N = roster size) from
        voters whose sequences are BEFORE the target sequence.

        Example: If roster_size=5 and target_sequence=010, we tally votes
        from sequences 005, 006, 007, 008, 009 (the 5 most recent before 010).

        Uses Borda Count: 1st choice gets N points, 2nd gets N-1, etc.
        """
        if not self.votes_file.exists():
            return {}

        roster_size = self._get_roster_size()
        target_seq_int = int(target_sequence)

        # Determine which voter sequences are eligible (last N before target)
        # E.g., if target=010 and roster=5, eligible = [005, 006, 007, 008, 009]
        eligible_start = max(1, target_seq_int - roster_size)
        eligible_sequences = set(f"{i:03}" for i in range(eligible_start, target_seq_int))

        tally = {}
        with open(self.votes_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                voter_seq = row['voter_sequence']
                if voter_seq not in eligible_sequences:
                    continue

                # Parse candidates array (comma-separated)
                candidates_str = row.get('candidates', '')
                if not candidates_str:
                    continue
                candidates = [c.strip() for c in candidates_str.split(',')]

                # Assign Borda points: Rank 1 gets roster_size, Rank 2 gets roster_size - 1, etc.
                for rank, persona in enumerate(candidates, start=1):
                    points = max(0, roster_size - (rank - 1))
                    tally[persona] = tally.get(persona, 0) + points
        return tally

    def apply_votes(self, sequence_id: str) -> Optional[str]:
        """
        Find the winner for a sequence and update schedule.csv.

        Tiebreaker: If multiple personas have the same points, the winner is
        the one who has NOT been chosen for the longest time (fairness priority).
        """
        tally = self.get_tally(sequence_id)
        if not tally:
            return None

        # Find max points
        max_points = max(tally.values())
        top_candidates = [p for p, pts in tally.items() if pts == max_points]

        if len(top_candidates) == 1:
            winner = top_candidates[0]
        else:
            # Tiebreaker: persona who waited longest (smallest last_chosen sequence)
            winner = min(
                top_candidates,
                key=lambda p: self._get_last_chosen_sequence(p, sequence_id)
            )

        if self._update_schedule(sequence_id, winner):
            return winner
        return None

    def _get_last_chosen_sequence(self, persona_id: str, before_sequence: str) -> int:
        """
        Get the last sequence where this persona was scheduled.
        Returns -1 if never scheduled (longest wait = highest priority).
        """
        if not self.schedule_file.exists():
            return -1

        last_seq = -1
        before_seq_int = int(before_sequence)

        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq = int(row['sequence'])
                if seq >= before_seq_int:
                    continue  # Only look at past sequences
                if row.get('persona') == persona_id:
                    last_seq = max(last_seq, seq)

        return last_seq

    def _update_schedule(self, sequence_id: str, persona_id: str) -> bool:
        """Update the persona for a specific sequence in schedule.csv."""
        if not self.schedule_file.exists():
            return False

        updated = False
        rows = []
        headers = []

        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            for row in reader:
                if row['sequence'] == sequence_id:
                    if not (row.get('session_id') or row.get('pr_status')):
                        row['persona'] = persona_id
                        updated = True
                rows.append(row)

        if updated:
            with open(self.schedule_file, mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)

        return updated

    def get_current_sequence(self, persona_id: str) -> Optional[str]:
        """Find the most recent active or started sequence for a persona."""
        if not self.schedule_file.exists():
            return None

        # We look for the latest entry for this persona that has a session_id
        # (meaning it's the current session)
        latest_seq = None
        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['persona'] == persona_id and row.get('session_id'):
                    latest_seq = row['sequence']
        return latest_seq

    def get_upcoming_winners(self, from_sequence: str, count: int = 5) -> List[Dict]:
        """Get current vote winners for upcoming sequences."""
        results = []
        start_seq = int(from_sequence)

        for i in range(count):
            seq_id = f"{start_seq + i:03}"
            tally = self.get_tally(seq_id)
            if tally:
                winner = max(tally, key=tally.get)
                results.append({
                    "sequence": seq_id,
                    "winner": winner,
                    "points": tally[winner],
                    "total_votes": sum(tally.values())
                })
            else:
                # Get scheduled persona if no votes
                scheduled = self._get_scheduled_persona(seq_id)
                if scheduled:
                    results.append({
                        "sequence": seq_id,
                        "winner": scheduled,
                        "points": 0,
                        "total_votes": 0,
                        "scheduled": True
                    })
        return results

    def _get_scheduled_persona(self, sequence_id: str) -> Optional[str]:
        """Get the currently scheduled persona for a sequence."""
        if not self.schedule_file.exists():
            return None
        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['sequence'] == sequence_id:
                    return row.get('persona')
        return None

    def validate_schedule_vs_votes(self) -> List[Dict]:
        """Validate that schedule.csv respects vote results. Returns list of violations."""
        violations = []
        if not self.schedule_file.exists() or not self.votes_file.exists():
            return violations

        with open(self.schedule_file, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq_id = row['sequence']
                scheduled_persona = row.get('persona')

                # Skip already executed sequences
                if row.get('session_id') or row.get('pr_status'):
                    continue

                tally = self.get_tally(seq_id)
                if tally:
                    winner = max(tally, key=tally.get)
                    if winner != scheduled_persona:
                        violations.append({
                            "sequence": seq_id,
                            "scheduled": scheduled_persona,
                            "voted_winner": winner,
                            "winner_points": tally[winner]
                        })
        return violations
