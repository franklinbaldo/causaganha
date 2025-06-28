#!/usr/bin/env python3
"""
Async Diario Pipeline - Bulk download and archive TJRO diarios to Internet Archive

This script processes the pipeline-ready diarios list and handles:
- Concurrent PDF downloads from TJRO
- Parallel uploads to Internet Archive
- Progress tracking and resume capability
- Error handling and retry logic
- Rate limiting to be respectful to TJRO servers
"""

import asyncio
import aiohttp
import json
import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from src.utils.logging_config import setup_logging, get_logger, set_tribunal_code
import argparse
from datetime import datetime, date, timezone
import hashlib
import subprocess
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor

from .download_orchestrator import DownloadOrchestrator

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not available, continue without it


# Configure Internet Archive with environment variables
def configure_ia() -> bool:
    """Configure Internet Archive credentials from environment variables."""
    access_key = os.getenv("IA_ACCESS_KEY")
    secret_key = os.getenv("IA_SECRET_KEY")

    if access_key and secret_key:
        try:
            from pathlib import Path
            import configparser

            # Create IA config file
            config_dir = Path.home() / ".config" / "internetarchive"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "ia.ini"

            config = configparser.ConfigParser()
            config["s3"] = {"access": access_key, "secret": secret_key}
            config["general"] = {"screenname": "causaganha-bot"}
            config["cookies"] = {}

            with open(config_file, "w") as f:
                config.write(f)

            logging.info("Internet Archive configured successfully")
            return True
        except Exception as e:
            logging.warning(f"Failed to configure IA: {e}")
            return False
    else:
        logging.warning("IA_ACCESS_KEY or IA_SECRET_KEY not found in environment")
        return False


# Configuration (with environment variable support)
CPU_COUNT = os.cpu_count() or 1
MAX_CONCURRENT_DOWNLOADS = int(
    os.getenv("MAX_CONCURRENT_DOWNLOADS", str(min(8, CPU_COUNT * 2)))
)  # Dynamic default based on CPU cores
MAX_CONCURRENT_IA_UPLOADS = int(
    os.getenv("MAX_CONCURRENT_IA_UPLOADS", "2")
)  # Internet Archive rate limiting
DOWNLOAD_TIMEOUT = 300  # 5 minutes per PDF
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_DOWNLOADS = 2.0  # Seconds between downloads
TRY_DIRECT_UPLOAD_DEFAULT = os.getenv("TRY_DIRECT_UPLOAD", "true").lower() == "true"


@dataclass
class ProcessingStatus:
    """Track processing status for each diario."""

    ia_identifier: str
    original_filename: str
    full_url: str
    date: str
    status: str = (
        "pending"  # pending, downloading, downloaded, uploading, completed, failed
    )
    local_path: Optional[str] = None
    ia_url: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 0
    sha256_hash: Optional[str] = None
    file_size: Optional[int] = None
    processing_time: Optional[float] = None


class AsyncDiarioPipeline:
    """Main async pipeline for processing TJRO diarios."""

    def __init__(
        self,
        data_dir: Path = Path("data"),
        progress_file: Path = Path("data/diario_pipeline_progress.json"),
        max_concurrent_downloads: int = MAX_CONCURRENT_DOWNLOADS,
        max_concurrent_uploads: int = MAX_CONCURRENT_IA_UPLOADS,
        try_direct_upload: bool = True,
    ):
        self.data_dir = data_dir
        self.progress_file = progress_file
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_uploads = max_concurrent_uploads
        self.try_direct_upload = try_direct_upload
        self.logger = get_logger(__name__)

        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "diarios").mkdir(exist_ok=True)

        # Processing tracking
        self.status_tracker: Dict[str, ProcessingStatus] = {}
        self.download_semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self.upload_semaphore = asyncio.Semaphore(max_concurrent_uploads)

        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def load_progress(self) -> None:
        """Load existing progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    progress_data = json.load(f)

                self.status_tracker = {
                    key: ProcessingStatus(**data) for key, data in progress_data.items()
                }

                completed = len(
                    [s for s in self.status_tracker.values() if s.status == "completed"]
                )
                total = len(self.status_tracker)
                self.logger.info(f"Loaded progress: {completed}/{total} completed")

            except Exception as e:
                self.logger.error(f"Failed to load progress: {e}")
                self.status_tracker = {}

    def save_progress(self) -> None:
        """Save current progress to file."""
        try:
            progress_data = {
                key: asdict(status) for key, status in self.status_tracker.items()
            }

            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")

    def get_statistics(self) -> Dict:
        """Get current processing statistics."""
        statuses = [s.status for s in self.status_tracker.values()]

        return {
            "total": len(statuses),
            "pending": statuses.count("pending"),
            "downloading": statuses.count("downloading"),
            "downloaded": statuses.count("downloaded"),
            "uploading": statuses.count("uploading"),
            "completed": statuses.count("completed"),
            "failed": statuses.count("failed"),
            "completion_rate": statuses.count("completed") / len(statuses) * 100
            if statuses
            else 0,
        }

    async def download_pdf(self, diario_data: Dict, status: ProcessingStatus) -> bool:
        """Download a single PDF with retries."""
        async with self.download_semaphore:
            status.status = "downloading"
            status.attempts += 1
            start_time = time.time()

            try:
                local_path = (
                    self.data_dir / "diarios" / diario_data["original_filename"]
                )

                # Skip if already exists and has valid size
                if (
                    local_path.exists() and local_path.stat().st_size > 1000
                ):  # At least 1KB
                    status.local_path = str(local_path)
                    status.status = "downloaded"
                    status.file_size = local_path.stat().st_size
                    status.sha256_hash = await self._calculate_sha256(local_path)
                    self.logger.info(f"Skipping existing file: {local_path.name}")
                    return True

                self.logger.info(f"Downloading: {diario_data['full_url']}")

                async with self.session.get(diario_data["full_url"]) as response:
                    if response.status == 200:
                        content = await response.read()

                        # Validate it's actually a PDF
                        if not content.startswith(b"%PDF"):
                            raise ValueError("Downloaded content is not a valid PDF")

                        # Write to file
                        with open(local_path, "wb") as f:
                            f.write(content)

                        # Update status
                        status.local_path = str(local_path)
                        status.status = "downloaded"
                        status.file_size = len(content)
                        status.sha256_hash = hashlib.sha256(content).hexdigest()
                        status.processing_time = time.time() - start_time

                        self.logger.info(
                            f"Downloaded: {local_path.name} ({len(content):,} bytes)"
                        )

                        # Respectful delay
                        await asyncio.sleep(DELAY_BETWEEN_DOWNLOADS)
                        return True

                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}",
                        )

            except Exception as e:
                status.error_message = str(e)
                self.logger.error(
                    f"Download failed for {diario_data['original_filename']}: {e}"
                )

                if status.attempts >= RETRY_ATTEMPTS:
                    status.status = "failed"
                    return False
                else:
                    status.status = "pending"  # Will retry
                    await asyncio.sleep(
                        min(status.attempts * 2, 10)
                    )  # Exponential backoff
                    return False

    async def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file asynchronously."""

        def _hash_file():
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, _hash_file)

    async def check_ia_exists(self, ia_identifier: str) -> bool:
        """Check if item already exists in Internet Archive."""
        try:
            metadata_url = f"https://archive.org/metadata/{ia_identifier}"
            async with self.session.head(metadata_url) as response:
                return response.status == 200
        except Exception:
            return False

    def upload_to_ia_local(self, diario_data: Dict, status: ProcessingStatus) -> bool:
        """Upload PDF to Internet Archive from local file."""
        if not status.local_path or not Path(status.local_path).exists():
            self.logger.error(f"Local file not available for {status.ia_identifier}")
            return False

        status.status = "uploading"

        try:
            # Prepare IA metadata
            metadata = diario_data["metadata"].copy()
            metadata["sha256"] = status.sha256_hash
            metadata["originalurl"] = diario_data["full_url"]
            metadata["addeddate"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            metadata["upload_method"] = "local_download_first"

            # Build ia command
            ia_cmd = [
                "ia",
                "upload",
                status.ia_identifier,
                status.local_path,
            ]

            # Add metadata as command line arguments
            for key, value in metadata.items():
                if value:  # Skip empty values
                    ia_cmd.extend([f"--metadata={key}:{value}"])

            # Execute upload
            self.logger.info(f"Uploading local file to IA: {status.ia_identifier}")
            result = subprocess.run(
                ia_cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            if result.returncode == 0:
                status.status = "completed"
                status.ia_url = f"https://archive.org/details/{status.ia_identifier}"
                self.logger.info(f"✅ Local IA upload completed: {status.ia_url}")

                # Remove local file to save space after successful upload
                try:
                    Path(status.local_path).unlink()
                    self.logger.info(f"Cleaned up local file: {status.local_path}")
                except Exception as cleanup_error:
                    self.logger.warning(
                        f"Failed to cleanup local file: {cleanup_error}"
                    )

                return True
            else:
                error_details = f"stdout: {result.stdout}, stderr: {result.stderr}"
                self.logger.error(
                    f"IA upload command failed with return code {result.returncode}: {error_details}"
                )
                raise subprocess.CalledProcessError(
                    result.returncode, ia_cmd, result.stdout, result.stderr
                )

        except Exception as e:
            status.error_message = str(e)
            status.status = "failed"
            self.logger.error(f"Local IA upload failed for {status.ia_identifier}: {e}")
            return False

    async def upload_to_ia_async(
        self, diario_data: Dict, status: ProcessingStatus
    ) -> bool:
        """Async wrapper for IA upload."""
        async with self.upload_semaphore:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                return await loop.run_in_executor(
                    executor, self.upload_to_ia_local, diario_data, status
                )

    async def process_diario(
        self, diario_data: Dict, skip_existing: bool = True
    ) -> bool:
        """Process a single diario: check if exists, download, then upload to IA."""
        ia_identifier = diario_data["ia_identifier"]

        # Get or create status tracker
        if ia_identifier not in self.status_tracker:
            self.status_tracker[ia_identifier] = ProcessingStatus(
                ia_identifier=ia_identifier,
                original_filename=diario_data["original_filename"],
                full_url=diario_data["full_url"],
                date=diario_data["date"],
            )

        status = self.status_tracker[ia_identifier]

        # Skip if already completed
        if status.status == "completed":
            self.logger.info(f"Already completed: {ia_identifier}")
            return True

        # Check if item already exists in IA
        if skip_existing and status.status == "pending":
            exists = await self.check_ia_exists(ia_identifier)
            if exists:
                status.status = "completed"
                status.ia_url = f"https://archive.org/details/{ia_identifier}"
                self.logger.info(f"✅ Item already exists in IA: {status.ia_url}")
                self.save_progress()
                return True

        # Download phase
        if status.status not in ["downloaded", "uploading"]:
            self.logger.info(f"Downloading {ia_identifier}")
            download_success = await self.download_pdf(diario_data, status)
            if not download_success:
                return False

            # Save progress after download
            self.save_progress()

        # Upload phase
        if status.status == "downloaded":
            upload_success = await self.upload_to_ia_async(diario_data, status)

            # Save progress after upload attempt
            self.save_progress()
            return upload_success

        return status.status == "completed"

    async def run_pipeline(
        self,
        diarios_data: List[Dict],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_items: Optional[int] = None,
        skip_existing: bool = True,
        use_queue: bool = True,
    ) -> None:
        """Run the complete async pipeline."""

        # Filter by date range if specified
        if start_date or end_date:
            filtered_diarios = []
            for diario in diarios_data:
                diario_date = date.fromisoformat(diario["date"])

                include = True
                if start_date and diario_date < date.fromisoformat(start_date):
                    include = False
                if end_date and diario_date > date.fromisoformat(end_date):
                    include = False

                if include:
                    filtered_diarios.append(diario)

            diarios_data = filtered_diarios
            self.logger.info(f"Filtered to {len(diarios_data)} diarios in date range")

        # Limit number of items if specified
        if max_items:
            diarios_data = diarios_data[:max_items]
            self.logger.info(f"Limited to {max_items} diarios")

        self.logger.info(f"Starting pipeline for {len(diarios_data)} diarios")

        if use_queue:
            orchestrator = DownloadOrchestrator(self.max_concurrent_downloads)
            await orchestrator.run(diarios_data, self)
        else:
            semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

            async def process_with_semaphore(diario_data):
                async with semaphore:
                    return await self.process_diario(
                        diario_data, skip_existing=skip_existing
                    )

            tasks = [process_with_semaphore(diario) for diario in diarios_data]

            completed = 0
            total = len(tasks)

            for task in asyncio.as_completed(tasks):
                try:
                    await task
                    completed += 1
                    if completed % 10 == 0 or completed == total:
                        stats = self.get_statistics()
                        self.logger.info(
                            f"Progress: {completed}/{total} processed "
                            f"({stats['completion_rate']:.1f}% complete, "
                            f"{stats['failed']} failed)"
                        )
                except Exception as e:
                    self.logger.error(f"Task failed: {e}")
                    completed += 1

        final_stats = self.get_statistics()
        self.logger.info("Pipeline completed!")
        self.logger.info(f"Final statistics: {final_stats}")


async def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Async pipeline for TJRO diarios download and IA upload"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/diarios_pipeline_ready.json"),
        help="Pipeline-ready JSON file",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory for downloads",
    )
    parser.add_argument(
        "--max-items", type=int, help="Maximum number of items to process (for testing)"
    )
    parser.add_argument("--start-date", type=str, help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date filter (YYYY-MM-DD)")
    parser.add_argument(
        "--concurrent-downloads",
        type=int,
        default=MAX_CONCURRENT_DOWNLOADS,
        help="Max concurrent downloads",
    )
    parser.add_argument(
        "--concurrent-uploads",
        type=int,
        default=MAX_CONCURRENT_IA_UPLOADS,
        help="Max concurrent IA uploads",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from previous progress"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Show statistics only"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Reprocess items even if they already exist in IA",
    )
    parser.add_argument(
        "--sync-database",
        action="store_true",
        help="Sync database with IA before processing",
    )
    parser.add_argument(
        "--upload-database",
        action="store_true",
        help="Upload database to IA after processing",
    )

    args = parser.parse_args()

    # Setup logging with structured format
    setup_logging("DEBUG" if args.verbose else "INFO", fmt="json")
    set_tribunal_code("tjro")

    # Configure Internet Archive
    if not configure_ia():
        logging.error(
            "Failed to configure Internet Archive. Please check IA_ACCESS_KEY and IA_SECRET_KEY environment variables."
        )
        return 1

    # Database sync before processing
    if args.sync_database:
        try:
            from ia_database_sync import IADatabaseSync

            db_sync = IADatabaseSync()

            logging.info("🔄 Syncing database with Internet Archive...")
            sync_result = db_sync.smart_sync(prefer_local=True)
            logging.info(f"Database sync result: {sync_result}")

            if sync_result in ["upload_failed", "download_failed"]:
                logging.error("Database sync failed, continuing with local database")

        except Exception as e:
            logging.error(f"Database sync failed: {e}")
            logging.info("Continuing with local database")

    # Load diarios data
    try:
        with open(args.input, "r") as f:
            diarios_data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {args.input}: {e}")
        return 1

    # Initialize pipeline
    progress_file = args.data_dir / "diario_pipeline_progress.json"

    async with AsyncDiarioPipeline(
        data_dir=args.data_dir,
        progress_file=progress_file,
        max_concurrent_downloads=args.concurrent_downloads,
        max_concurrent_uploads=args.concurrent_uploads,
    ) as pipeline:
        # Load existing progress if resuming
        if args.resume:
            pipeline.load_progress()

        # Show stats if requested
        if args.stats_only:
            if pipeline.status_tracker:
                stats = pipeline.get_statistics()
                print("📊 Pipeline Statistics:")
                print(f"   Total: {stats['total']}")
                print(
                    f"   Completed: {stats['completed']} ({stats['completion_rate']:.1f}%)"
                )
                print(f"   Failed: {stats['failed']}")
                print(f"   Pending: {stats['pending']}")
                print(f"   In Progress: {stats['downloading'] + stats['uploading']}")
            else:
                print("No progress data found.")
            return 0

        # Run the pipeline
        await pipeline.run_pipeline(
            diarios_data,
            start_date=args.start_date,
            end_date=args.end_date,
            max_items=args.max_items,
            skip_existing=not args.force_reprocess,
            use_queue=True,
        )

        # Database upload after processing
        if args.upload_database:
            try:
                from ia_database_sync import IADatabaseSync

                db_sync = IADatabaseSync()

                logging.info("⬆️ Uploading updated database to Internet Archive...")
                success = db_sync.upload_database_to_ia()

                if success:
                    logging.info("✅ Database uploaded successfully")
                else:
                    logging.error("❌ Database upload failed")

            except Exception as e:
                logging.error(f"Database upload failed: {e}")

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
