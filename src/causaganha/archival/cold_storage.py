import logging
import os
import tarfile
from datetime import UTC, date, datetime, timedelta

import boto3

from causaganha.storage.connection import get_connection


logger = logging.getLogger(__name__)


class ColdStorageArchiver:
    def __init__(self, s3_bucket: str = "causaganha-archive"):
        self.s3_client = boto3.client("s3")
        self.s3_bucket = s3_bucket

    def check_archival_eligible_data(self) -> list[dict]:
        """Check for archival-eligible data: Tribunals with 100% coverage for 6+ consecutive months.
        Keep rolling 3-month window hot (fast access).
        Archive older data.
        """
        eligible_data = []
        con = get_connection()

        # Calculate cutoff date for 3 months hot window
        three_months_ago = (datetime.now(UTC) - timedelta(days=90)).strftime("%Y-%m-%d")
        nine_months_ago = (datetime.now(UTC) - timedelta(days=270)).strftime("%Y-%m-%d")

        # Find tribunals and months that have completed exports
        # older than 3 months but newer than 9 months (6 months window)
        # We group by tribunal, year, and month.
        query = """
            SELECT
                tribunal,
                EXTRACT(year FROM partition_date) as yr,
                EXTRACT(month FROM partition_date) as mo,
                COUNT(*) as days_exported
            FROM parquet_exports
            WHERE status = 'completed'
              AND partition_date < ?
              AND partition_date >= ?
            GROUP BY tribunal, yr, mo
            HAVING COUNT(*) >= 20 -- Roughly 20 working days = ~100% coverage for a month
        """

        try:
            results = con.con.execute(query, [three_months_ago, nine_months_ago]).fetchall()

            for row in results:
                tribunal, yr, mo, days_exported = row
                yr = int(yr)
                mo = int(mo)

                # Check if already archived
                archived_check = con.con.execute(
                    "SELECT 1 FROM archival_log WHERE tribunal = ? AND archive_year = ? AND archive_month = ?",
                    [tribunal, yr, mo],
                ).fetchone()

                if not archived_check:
                    # Get actual files for this month
                    files_query = """
                        SELECT parquet_filename
                        FROM parquet_exports
                        WHERE tribunal = ?
                          AND EXTRACT(year FROM partition_date) = ?
                          AND EXTRACT(month FROM partition_date) = ?
                          AND status = 'completed'
                    """
                    files_results = con.con.execute(files_query, [tribunal, yr, mo]).fetchall()
                    actual_files = [f[0] for f in files_results if f[0] and os.path.exists(f[0])]

                    if actual_files:
                        eligible_data.append(
                            {"tribunal": tribunal, "year": yr, "month": mo, "files": actual_files}
                        )
                    else:
                        logger.warning(
                            f"No valid local parquet files found for {tribunal} {yr}-{mo:02d}"
                        )

        except Exception as e:
            logger.error(f"Error checking archival eligible data: {e}")

        return eligible_data

    def archive_data(self, tribunal: str, year: int, month: int, file_paths: list[str]):
        """Create tarball and upload to S3 Glacier, then update metadata and delete local files.
        If S3 upload fails, raises exception and aborts deletion/purging.
        """
        tarball_name = f"tribunal_{tribunal}_{year}-{month:02d}.tar.gz"
        tarball_path = f"/tmp/{tarball_name}"

        logger.info(f"Creating tarball {tarball_path} for {tribunal} {year}-{month:02d}")

        # 1. Create tarball with actual files
        with tarfile.open(tarball_path, "w:gz") as tar:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    tar.add(file_path, arcname=os.path.basename(file_path))
                else:
                    logger.warning(f"File not found during tar creation: {file_path}")

        # 2. Upload to S3 Glacier
        s3_key = f"cold/{year}/{tribunal}/{tarball_name}"
        logger.info(f"Uploading to s3://{self.s3_bucket}/{s3_key} (Glacier)")

        # We DO NOT catch exceptions here. If S3 upload fails, we must crash
        # to prevent deleting the source files or purging DB records.
        self.s3_client.upload_file(
            tarball_path, self.s3_bucket, s3_key, ExtraArgs={"StorageClass": "GLACIER"}
        )
        logger.info("Upload to S3 successful")

        # 3. Update metadata
        self._update_metadata(tribunal, year, month, s3_key)

        # 4. Delete from hot storage (Only happens if S3 upload succeeded)
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted hot file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete hot file {file_path}: {e}")

        # 5. Purge old data from database (Only happens if S3 upload succeeded)
        self._purge_hot_database_records(tribunal, year, month)

        # Cleanup tarball
        if os.path.exists(tarball_path):
            os.remove(tarball_path)

    def _update_metadata(self, tribunal: str, year: int, month: int, s3_key: str):
        con = get_connection()
        try:
            con.con.execute(
                """
                INSERT INTO archival_log (tribunal, archive_year, archive_month, s3_key, status, archived_at)
                VALUES (?, ?, ?, ?, 'archived', CURRENT_TIMESTAMP)
            """,
                [tribunal, year, month, s3_key],
            )
            logger.info(f"Updated archival_log for {tribunal} {year}-{month:02d}")
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            raise e

    def _purge_hot_database_records(self, tribunal: str, year: int, month: int):
        con = get_connection()
        try:
            # First day of month
            start_date = date(year, month, 1)
            # Last day of month
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)

            start_str = start_date.isoformat()
            end_str = end_date.isoformat()

            # Delete intimations that match this tribunal and month window
            con.con.execute(
                """
                DELETE FROM intimations
                WHERE sigla_tribunal = ?
                  AND data_disponibilizacao >= ?
                  AND data_disponibilizacao <= ?
                """,
                [tribunal, start_str, end_str],
            )
            logger.info(f"Purged old intimations from hot DB for {tribunal} {year}-{month:02d}")
        except Exception as e:
            logger.error(f"Failed to purge hot database records: {e}")
            raise e

    def trigger_restore(self, tribunal: str, year: int, month: int) -> bool:
        """Trigger S3 restore for archived data (SLA 3-6 hours).
        Raises exception if S3 interaction fails.
        """
        con = get_connection()

        # Find s3 key
        result = con.con.execute(
            "SELECT s3_key FROM archival_log WHERE tribunal = ? AND archive_year = ? AND archive_month = ?",
            [tribunal, year, month],
        ).fetchone()

        if not result:
            logger.error(f"No archive found for {tribunal} {year}-{month:02d}")
            return False

        s3_key = result[0]

        logger.info(f"Triggering restore for s3://{self.s3_bucket}/{s3_key}")

        # Let boto3 exception bubble up if it fails
        self.s3_client.restore_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            RestoreRequest={
                "Days": 7,  # Keep restored data for 7 days
                "GlacierJobParameters": {
                    "Tier": "Standard"  # 3-5 hours retrieval time
                },
            },
        )

        # Update status
        con.con.execute(
            "UPDATE archival_log SET status = 'restoring' WHERE tribunal = ? AND archive_year = ? AND archive_month = ?",
            [tribunal, year, month],
        )

        return True
