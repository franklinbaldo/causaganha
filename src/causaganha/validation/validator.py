"""Data validation logic using Ibis."""

from typing import Any

from ibis import BaseBackend


class DataValidator:
    """Validates data integrity and quality in the database."""

    def __init__(self, con: BaseBackend):
        """Initialize the validator.

        Args:
            con: Ibis DuckDB connection backend.
        """
        self.con = con

    def check_intimations(self) -> dict[str, Any]:
        """Check intimations table for data issues.

        Returns:
            Dictionary with counts of issues found.
        """
        t = self.con.table("intimations")

        # Count total
        total = t.count().execute()

        # Check invalid links (simple check: must start with http)
        # Handle nulls safely
        invalid_links = t.filter(
            ~(t.link.startswith("http")) | t.link.isnull(),
        ).count().execute()

        # Check missing tribunal
        missing_tribunal = t.filter(t.sigla_tribunal.isnull()).count().execute()

        return {
            "total_checked": total,
            "invalid_links": invalid_links,
            "missing_tribunal": missing_tribunal,
        }

    def check_orphaned_analysis(self) -> list[int]:
        """Check for analysis results that reference non-existent intimations.

        Returns:
            List of orphaned analysis result IDs.
        """
        analysis = self.con.table("analysis_results")
        intimations = self.con.table("intimations")

        # Left join analysis -> intimations
        joined = analysis.left_join(
            intimations, analysis.intimation_id == intimations.id,
        )

        # Filter where intimation id is null (meaning no match found)
        orphans = joined.filter(intimations.id.isnull()).select(analysis.id)

        # Return list of IDs
        # to_py() returns a list of dictionaries if selecting fields, or scalars?
        # Actually ibis to_py() usually returns pandas df or list of tuples/dicts.
        # Using execute().to_dict('records') or similar via pandas might be safer
        # but to_py() is cleaner if works.
        # Let's use execute() to get a pandas df, then extract the column.
        df = orphans.execute()
        return df["id"].tolist()

    def check_ratings(self) -> dict[str, Any]:
        """Check lawyer ratings table for invalid values.

        Returns:
            Dictionary with counts of issues found.
        """
        t = self.con.table("lawyer_ratings")

        invalid_sigma = t.filter(t.sigma <= 0).count().execute()

        return {
            "invalid_sigma": invalid_sigma,
        }
