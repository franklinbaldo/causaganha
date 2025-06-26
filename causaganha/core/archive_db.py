# causaganha/core/archive_db.py
"""
Internet Archive integration for CausaGanha database snapshots.

Provides functionality to archive DuckDB snapshots to Internet Archive
for public access, research, and long-term preservation.
"""

import os
import json
import logging
import subprocess
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .database import CausaGanhaDB

logger = logging.getLogger(__name__)


@dataclass
class IAConfig:
    """Configuration for Internet Archive uploads."""

    access_key: str
    secret_key: str

    @classmethod
    def from_env(cls) -> "IAConfig":
        """Create IA config from environment variables."""
        access_key = os.getenv("IA_ACCESS_KEY")
        secret_key = os.getenv("IA_SECRET_KEY")

        if not access_key or not secret_key:
            raise ValueError(
                "Missing required IA environment variables: IA_ACCESS_KEY, IA_SECRET_KEY"
            )

        return cls(access_key=access_key, secret_key=secret_key)


class DatabaseArchiver:
    """
    Handles archiving of CausaGanha database snapshots to Internet Archive.

    Features:
    - Weekly and monthly database snapshots
    - Compressed uploads with metadata
    - Public access for research and transparency
    - Integration with existing IA infrastructure
    """

    def __init__(self, ia_config: IAConfig):
        self.ia_config = ia_config
        self._configure_ia_auth()

    def _configure_ia_auth(self):
        """Configure Internet Archive authentication."""
        # Set environment variables for ia CLI tool
        os.environ["IA_ACCESS"] = self.ia_config.access_key
        os.environ["IA_SECRET"] = self.ia_config.secret_key
        logger.info("Internet Archive authentication configured")

    def create_database_item_id(
        self, snapshot_date: date, archive_type: str = "weekly"
    ) -> str:
        """Create IA item identifier for database snapshot."""
        date_str = snapshot_date.strftime("%Y-%m-%d")
        return f"causaganha-database-{date_str}-{archive_type}"

    def create_archive_metadata(
        self, snapshot_date: date, archive_type: str, db_stats: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate Internet Archive metadata for database snapshot."""
        date_str = snapshot_date.strftime("%Y-%m-%d")

        metadata = {
            "title": f"CausaGanha TrueSkill Database - {date_str}",
            "creator": "CausaGanha Project",
            "date": date_str,
            "description": (
                f"Judicial decision analysis database using TrueSkill rating system from "
                f"Tribunal de Justiça de Rondônia (TJRO). Contains lawyer performance "
                f"ratings, match history, and decision metadata. "
                f"Archive type: {archive_type}. "
                f"Total lawyers: {db_stats.get('total_advogados', 'N/A')}, "
                f"Total matches: {db_stats.get('total_partidas', 'N/A')}, "
                f"Total decisions: {db_stats.get('total_decisoes', 'N/A')}."
            ),
            "subject": ";".join(
                [
                    "legal-analytics",
                    "trueskill",
                    "judicial-decisions",
                    "rondonia",
                    "lawyer-performance",
                    "court-decisions",
                    "legal-research",
                ]
            ),
            "language": "por",
            "collection": "opensource_data",
            "mediatype": "data",
            "licenseurl": "https://creativecommons.org/licenses/by/4.0/",
            "archive_type": archive_type,
            "causaganha_version": "1.0.0",
            "data_source": "TJRO - Tribunal de Justiça de Rondônia",
            "rating_system": "Microsoft TrueSkill",
            "export_timestamp": datetime.now().isoformat(),
        }

        # Add statistics as metadata
        for key, value in db_stats.items():
            metadata[f"stats_{key}"] = str(value)

        return metadata

    def export_database_snapshot(
        self, db_path: Path, export_dir: Path, snapshot_date: date
    ) -> Dict[str, Path]:
        """
        Export database snapshot with multiple formats.

        Returns:
            Dict mapping format names to file paths
        """
        export_dir.mkdir(parents=True, exist_ok=True)

        date_str = snapshot_date.strftime("%Y%m%d")
        exports = {}

        logger.info("Exporting database snapshot for %s", snapshot_date)

        with CausaGanhaDB(db_path) as db:
            # 1. Export compressed DuckDB file
            db_export_path = export_dir / f"causaganha_database_{date_str}.duckdb"

            # Use DuckDB COPY command for consistent snapshot
            db.conn.execute(f"EXPORT DATABASE '{db_export_path}' (FORMAT DUCKDB)")
            exports["database"] = db_export_path

            logger.info("Exported DuckDB file: %s", db_export_path)

            # 2. Export individual tables as CSV
            csv_dir = export_dir / "csv_exports"
            csv_dir.mkdir(exist_ok=True)

            tables = ["ratings", "partidas", "pdf_metadata", "decisoes", "json_files"]

            for table in tables:
                try:
                    df = db.conn.execute(f"SELECT * FROM {table}").df()
                    csv_path = csv_dir / f"{table}_{date_str}.csv"
                    df.to_csv(csv_path, index=False)
                    exports[f"csv_{table}"] = csv_path
                    logger.info(
                        "Exported %s: %d records to %s", table, len(df), csv_path
                    )
                except Exception as e:
                    logger.warning("Failed to export table %s: %s", table, e)

            # 3. Export metadata and statistics
            stats = db.get_statistics()
            metadata_path = export_dir / f"export_metadata_{date_str}.json"

            export_metadata = {
                "export_date": snapshot_date.isoformat(),
                "export_timestamp": datetime.now().isoformat(),
                "database_path": str(db_path),
                "database_size_mb": round(db_path.stat().st_size / (1024 * 1024), 2),
                "statistics": stats,
                "exported_files": {k: str(v) for k, v in exports.items()},
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(export_metadata, f, indent=2, ensure_ascii=False)

            exports["metadata"] = metadata_path
            logger.info("Exported metadata: %s", metadata_path)

        return exports

    def compress_exports(self, exports: Dict[str, Path], output_dir: Path) -> Path:
        """Compress all exports into a single archive."""
        date_str = datetime.now().strftime("%Y%m%d")
        archive_path = output_dir / f"causaganha_database_{date_str}.tar.gz"

        # Create tar.gz archive
        import tarfile

        with tarfile.open(archive_path, "w:gz") as tar:
            for export_type, file_path in exports.items():
                if file_path.is_file():
                    # Add file with relative path
                    arcname = file_path.name
                    tar.add(file_path, arcname=arcname)
                    logger.debug("Added %s to archive as %s", file_path, arcname)
                elif file_path.is_dir():
                    # Add directory contents
                    for sub_file in file_path.rglob("*"):
                        if sub_file.is_file():
                            arcname = str(sub_file.relative_to(file_path.parent))
                            tar.add(sub_file, arcname=arcname)
                            logger.debug("Added %s to archive as %s", sub_file, arcname)

        logger.info(
            "Created compressed archive: %s (%.2f MB)",
            archive_path,
            archive_path.stat().st_size / (1024 * 1024),
        )

        return archive_path

    def upload_to_internet_archive(
        self, archive_path: Path, item_id: str, metadata: Dict[str, str]
    ) -> bool:
        """Upload compressed archive to Internet Archive."""
        try:
            logger.info("Uploading %s to Internet Archive as %s", archive_path, item_id)

            # Prepare ia upload command
            cmd = ["ia", "upload", item_id, str(archive_path)]

            # Add metadata as command line arguments
            for key, value in metadata.items():
                cmd.extend([f"--metadata={key}:{value}"])

            # Add checksum for verification
            cmd.append("--checksum")

            # Execute upload
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes timeout
            )

            if result.returncode == 0:
                logger.info("Successfully uploaded to Internet Archive: %s", item_id)
                logger.info("Archive URL: https://archive.org/details/%s", item_id)
                return True
            else:
                logger.error("Upload failed. Return code: %d", result.returncode)
                logger.error("STDOUT: %s", result.stdout)
                logger.error("STDERR: %s", result.stderr)
                return False

        except subprocess.TimeoutExpired:
            logger.error("Upload timed out after 30 minutes")
            return False
        except (subprocess.SubprocessError, OSError) as e:
            logger.error("Upload failed with error: %s", e)
            return False

    def record_archive_success(
        self,
        db_path: Path,
        snapshot_date: date,
        archive_type: str,
        item_id: str,
        archive_path: Path,
        db_stats: Dict[str, Any],
    ) -> bool:
        """Record successful archive in the database."""
        try:
            with CausaGanhaDB(db_path) as db:
                # Calculate file hash
                import hashlib

                sha256_hash = hashlib.sha256()
                with open(archive_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                file_hash = sha256_hash.hexdigest()

                # Insert record
                db.conn.execute(
                    """
                    INSERT INTO archived_databases (
                        snapshot_date, archive_type, ia_identifier, ia_url,
                        file_size_bytes, sha256_hash, total_lawyers, total_matches,
                        total_decisions, upload_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    [
                        snapshot_date,
                        archive_type,
                        item_id,
                        f"https://archive.org/details/{item_id}",
                        archive_path.stat().st_size,
                        file_hash,
                        db_stats.get("total_advogados", 0),
                        db_stats.get("total_partidas", 0),
                        db_stats.get("total_decisoes", 0),
                        "completed",
                    ],
                )

                logger.info("Recorded archive success in database")
                return True

        except Exception as e:
            logger.error("Failed to record archive success: %s", e)
            return False

    def archive_database(
        self,
        db_path: Path = Path("data/causaganha.duckdb"),
        snapshot_date: Optional[date] = None,
        archive_type: str = "weekly",
    ) -> bool:
        """
        Complete database archive workflow.

        Args:
            db_path: Path to DuckDB database
            snapshot_date: Date for snapshot (defaults to today)
            archive_type: Type of archive (weekly, monthly, quarterly)

        Returns:
            True if archive was successful
        """
        if snapshot_date is None:
            snapshot_date = date.today()

        logger.info(
            "Starting database archive workflow for %s (%s)",
            snapshot_date,
            archive_type,
        )

        # Create temporary directory for exports
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "exports"

            try:
                # Get database statistics
                with CausaGanhaDB(db_path) as db:
                    db_stats = db.get_statistics()

                # Export database in multiple formats
                exports = self.export_database_snapshot(
                    db_path, export_dir, snapshot_date
                )

                # Compress exports
                archive_path = self.compress_exports(exports, Path(temp_dir))

                # Create IA metadata
                item_id = self.create_database_item_id(snapshot_date, archive_type)
                metadata = self.create_archive_metadata(
                    snapshot_date, archive_type, db_stats
                )

                # Upload to Internet Archive
                upload_success = self.upload_to_internet_archive(
                    archive_path, item_id, metadata
                )

                if upload_success:
                    # Record success in database
                    self.record_archive_success(
                        db_path,
                        snapshot_date,
                        archive_type,
                        item_id,
                        archive_path,
                        db_stats,
                    )
                    logger.info("Database archive completed successfully")
                    return True
                else:
                    logger.error("Database archive failed during upload")
                    return False

            except Exception as e:
                logger.error("Database archive failed: %s", e)
                return False


def main():
    """CLI interface for database archiving."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Archive CausaGanha database to Internet Archive"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("data/causaganha.duckdb"),
        help="Path to DuckDB database",
    )
    parser.add_argument(
        "--date", type=str, help="Snapshot date (YYYY-MM-DD, defaults to today)"
    )
    parser.add_argument(
        "--archive-type",
        choices=["weekly", "monthly", "quarterly"],
        default="weekly",
        help="Type of archive",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        # Parse date if provided
        snapshot_date = None
        if args.date:
            snapshot_date = datetime.strptime(args.date, "%Y-%m-%d").date()

        # Initialize archiver
        ia_config = IAConfig.from_env()
        archiver = DatabaseArchiver(ia_config)

        # Run archive
        success = archiver.archive_database(
            db_path=args.db_path,
            snapshot_date=snapshot_date,
            archive_type=args.archive_type,
        )

        if success:
            logger.info("✅ Database archive completed successfully")
            exit(0)
        else:
            logger.error("❌ Database archive failed")
            exit(1)

    except Exception as e:
        logger.error("Archive failed with error: %s", e)
        exit(1)


if __name__ == "__main__":
    main()
