#!/usr/bin/env python3
"""
Internet Archive Database Synchronization

This module provides functionality to sync the CausaGanha database with Internet Archive,
allowing both local development and GitHub Actions to work with the same shared database.
"""

import os
import json
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import hashlib
import duckdb

# Environment variables are loaded from system environment


class IADatabaseSync:
    """Manage database synchronization with Internet Archive."""

    def __init__(self, local_db_path: Path = Path("data/causaganha.duckdb")):
        self.local_db_path = Path(local_db_path)
        self.logger = logging.getLogger(__name__)

        # IA configuration
        self.ia_database_identifier = "causaganha-database-live"
        self.ia_database_filename = "causaganha.duckdb"
        self.ia_lock_identifier = "causaganha-database-lock"
        self.ia_lock_filename = "database.lock"

        # Metadata file to track sync status
        self.sync_metadata_path = (
            self.local_db_path.parent / ".database_sync_metadata.json"
        )

        # Configure IA if needed
        self._configure_ia()

    def _configure_ia(self) -> bool:
        """Configure Internet Archive credentials."""
        access_key = os.getenv("IA_ACCESS_KEY")
        secret_key = os.getenv("IA_SECRET_KEY")

        if not access_key or not secret_key:
            self.logger.warning("IA credentials not found in environment")
            return False

        try:
            import configparser

            # Create IA config file
            config_dir = Path.home() / ".config" / "internetarchive"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "ia.ini"

            config = configparser.ConfigParser()
            config["s3"] = {"access": access_key, "secret": secret_key}
            config["general"] = {"screenname": "causaganha-sync"}
            config["cookies"] = {}

            with open(config_file, "w") as f:
                config.write(f)

            self.logger.debug("IA configured for database sync")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure IA: {e}")
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _get_local_metadata(self) -> Dict[str, Any]:
        """Get local database metadata."""
        if not self.local_db_path.exists():
            return {}

        return {
            "file_size": self.local_db_path.stat().st_size,
            "modified_time": self.local_db_path.stat().st_mtime,
            "sha256": self._calculate_file_hash(self.local_db_path),
            "last_sync": None,
        }

    def _get_sync_metadata(self) -> Dict[str, Any]:
        """Load sync metadata from local file."""
        if not self.sync_metadata_path.exists():
            return {}

        try:
            with open(self.sync_metadata_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load sync metadata: {e}")
            return {}

    def _save_sync_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save sync metadata to local file."""
        try:
            with open(self.sync_metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save sync metadata: {e}")

    def _get_ia_metadata(self) -> Optional[Dict[str, Any]]:
        """Get database metadata from Internet Archive."""
        try:
            result = subprocess.run(
                ["ia", "metadata", self.ia_database_identifier],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                return metadata
            else:
                self.logger.debug(f"IA metadata query failed: {result.stderr}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to get IA metadata: {e}")
            return None

    def _get_ia_db_file_info(self) -> Optional[Dict[str, Any]]:
        """Return file info for the DuckDB file stored on IA."""
        ia_metadata = self._get_ia_metadata()
        if not ia_metadata:
            return None

        for file_info in ia_metadata.get("files", []):
            if file_info.get("name") == self.ia_database_filename:
                return file_info
        return None

    def database_exists_in_ia(self) -> bool:
        """Check if database exists in Internet Archive."""
        ia_metadata = self._get_ia_metadata()
        if not ia_metadata:
            return False

        # Check if the database file exists in the item
        files = ia_metadata.get("files", [])
        for file_info in files:
            if file_info.get("name") == self.ia_database_filename:
                return True

        return False

    def _check_lock_exists(self) -> Optional[Dict[str, Any]]:
        """Check if database lock exists in IA."""
        try:
            result = subprocess.run(
                ["ia", "metadata", self.ia_lock_identifier],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            return None

        except Exception as e:
            self.logger.debug(f"Lock check failed: {e}")
            return None

    def _create_lock(self, operation: str, timeout_minutes: int = 30) -> bool:
        """Create a lock in IA to prevent concurrent database operations."""
        try:
            # Create a temporary lock file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".lock", delete=False
            ) as f:
                lock_info = {
                    "operation": operation,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "created_by": os.getenv("USER", "unknown"),
                    "hostname": os.getenv("HOSTNAME", "unknown"),
                    "timeout_minutes": timeout_minutes,
                    "expires_at": (
                        datetime.now(timezone.utc).timestamp() + timeout_minutes * 60
                    ),
                }
                json.dump(lock_info, f, indent=2)
                temp_lock_path = f.name

            self.logger.info(f"Creating database lock for operation: {operation}")

            # Upload lock file to IA
            result = subprocess.run(
                [
                    "ia",
                    "upload",
                    self.ia_lock_identifier,
                    temp_lock_path,
                    "--metadata=title:CausaGanha Database Lock",
                    "--metadata=description:Temporary lock to prevent concurrent database operations",
                    "--metadata=mediatype:data",
                    f"--metadata=operation:{operation}",
                    f"--metadata=created_at:{lock_info['created_at']}",
                    f"--metadata=timeout_minutes:{timeout_minutes}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Clean up temp file
            os.unlink(temp_lock_path)

            if result.returncode == 0:
                self.logger.info(f"✅ Database lock created: {self.ia_lock_identifier}")
                return True
            else:
                self.logger.error(f"Failed to create lock: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to create lock: {e}")
            return False

    def _remove_lock(self) -> bool:
        """Remove the database lock from IA."""
        try:
            result = subprocess.run(
                ["ia", "delete", self.ia_lock_identifier],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.logger.info("🔓 Database lock removed")
                return True
            else:
                self.logger.warning(
                    f"Lock removal failed (may not exist): {result.stderr}"
                )
                return True  # Consider missing lock as success

        except Exception as e:
            self.logger.error(f"Failed to remove lock: {e}")
            return False

    def _wait_for_lock_release(self, max_wait_minutes: int = 60) -> bool:
        """Wait for existing lock to be released."""
        import time

        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60

        self.logger.info(
            f"Waiting for database lock to be released (max {max_wait_minutes} minutes)..."
        )

        while time.time() - start_time < max_wait_seconds:
            lock_metadata = self._check_lock_exists()

            if not lock_metadata:
                self.logger.info("✅ Lock released, proceeding")
                return True

            # Check if lock has expired
            try:
                lock_info = lock_metadata.get("metadata", {})
                created_at = lock_info.get("created_at")
                timeout_minutes = int(lock_info.get("timeout_minutes", 30))

                if created_at:
                    created_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    expired_time = created_time.timestamp() + (timeout_minutes * 60)

                    if time.time() > expired_time:
                        self.logger.warning("Lock has expired, removing it")
                        self._remove_lock()
                        return True

            except Exception as e:
                self.logger.debug(f"Error checking lock expiration: {e}")

            # Wait a bit before checking again
            time.sleep(30)  # Check every 30 seconds

            elapsed_minutes = (time.time() - start_time) / 60
            self.logger.info(
                f"Still waiting for lock release ({elapsed_minutes:.1f}/{max_wait_minutes} minutes)"
            )

        self.logger.error(
            f"Timeout waiting for lock release after {max_wait_minutes} minutes"
        )
        return False

    def download_database_from_ia(self, force: bool = False) -> bool:
        """Download database from Internet Archive."""
        if not force and self.local_db_path.exists():
            self.logger.info("Local database exists. Use force=True to overwrite.")
            return False

        if not self.database_exists_in_ia():
            self.logger.warning("Database not found in Internet Archive")
            return False

        try:
            # Create backup of existing local database
            if self.local_db_path.exists():
                backup_path = self.local_db_path.with_suffix(".backup")
                shutil.copy2(self.local_db_path, backup_path)
                self.logger.info(f"Created backup: {backup_path}")

            # Download from IA
            self.logger.info(
                f"Downloading database from IA: {self.ia_database_identifier}"
            )

            # Ensure parent directory exists
            self.local_db_path.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    "ia",
                    "download",
                    self.ia_database_identifier,
                    self.ia_database_filename,
                    "--destdir",
                    str(self.local_db_path.parent),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # Move downloaded file to correct location
                downloaded_file = (
                    self.local_db_path.parent
                    / self.ia_database_identifier
                    / self.ia_database_filename
                )
                if downloaded_file.exists():
                    shutil.move(str(downloaded_file), str(self.local_db_path))

                    # Clean up download directory
                    download_dir = (
                        self.local_db_path.parent / self.ia_database_identifier
                    )
                    if download_dir.exists():
                        shutil.rmtree(download_dir)

                    # Update sync metadata
                    local_metadata = self._get_local_metadata()
                    local_metadata["last_sync"] = datetime.now(timezone.utc).isoformat()
                    local_metadata["sync_direction"] = "download"
                    self._save_sync_metadata(local_metadata)

                    self.logger.info(
                        f"✅ Database downloaded successfully: {self.local_db_path}"
                    )
                    return True
                else:
                    self.logger.error("Downloaded file not found in expected location")
                    return False
            else:
                self.logger.error(f"IA download failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to download database: {e}")
            return False

    def upload_database_to_ia(
        self, force: bool = False, wait_for_lock: bool = True
    ) -> bool:
        """Upload local database to Internet Archive."""
        if not self.local_db_path.exists():
            self.logger.error("Local database not found")
            return False

        # Check for existing lock
        if not force:
            lock_metadata = self._check_lock_exists()
            if lock_metadata:
                if wait_for_lock:
                    if not self._wait_for_lock_release():
                        return False
                else:
                    self.logger.error("Database is locked by another operation")
                    return False

        # Check if upload is needed
        if not force:
            sync_metadata = self._get_sync_metadata()
            local_metadata = self._get_local_metadata()

            # Skip if file hasn't changed since last sync
            if (
                sync_metadata.get("sha256") == local_metadata["sha256"]
                and sync_metadata.get("sync_direction") == "upload"
            ):
                self.logger.info("Database unchanged since last upload, skipping")
                return True

        # Create lock for upload operation
        if not self._create_lock("upload", timeout_minutes=60):
            self.logger.error("Failed to create lock for upload operation")
            return False

        try:
            self.logger.info(f"Uploading database to IA: {self.ia_database_identifier}")

            # Prepare metadata
            local_metadata = self._get_local_metadata()
            upload_metadata = {
                "title": "CausaGanha Live Database",
                "description": "Live DuckDB database for CausaGanha judicial analysis system",
                "creator": "CausaGanha System",
                "subject": "database; judicial; legal; duckdb; causaganha",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "language": "por",
                "collection": "opensource",
                "mediatype": "data",
                "file_size": str(local_metadata["file_size"]),
                "sha256": local_metadata["sha256"],
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "sync_version": "1.0",
            }

            # Build IA upload command
            cmd = ["ia", "upload", self.ia_database_identifier, str(self.local_db_path)]

            # Add metadata
            for key, value in upload_metadata.items():
                cmd.extend([f"--metadata={key}:{value}"])

            # Execute upload
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                # Update sync metadata
                local_metadata["last_sync"] = datetime.now(timezone.utc).isoformat()
                local_metadata["sync_direction"] = "upload"
                local_metadata["ia_identifier"] = self.ia_database_identifier
                self._save_sync_metadata(local_metadata)

                self.logger.info(
                    f"✅ Database uploaded successfully: https://archive.org/details/{self.ia_database_identifier}"
                )

                # Remove lock after successful upload
                self._remove_lock()
                return True
            else:
                self.logger.error(f"IA upload failed: {result.stderr}")
                self._remove_lock()  # Remove lock on failure too
                return False

        except Exception as e:
            self.logger.error(f"Failed to upload database: {e}")
            self._remove_lock()  # Remove lock on exception
            return False

    def sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        local_exists = self.local_db_path.exists()
        ia_exists = self.database_exists_in_ia()

        # Check for lock
        lock_metadata = self._check_lock_exists()

        status = {
            "local_database_exists": local_exists,
            "ia_database_exists": ia_exists,
            "local_path": str(self.local_db_path),
            "ia_identifier": self.ia_database_identifier,
            "lock_exists": lock_metadata is not None,
            "lock_info": lock_metadata.get("metadata", {}) if lock_metadata else None,
        }

        if local_exists:
            status["local_metadata"] = self._get_local_metadata()
            status["sync_metadata"] = self._get_sync_metadata()

        if ia_exists:
            ia_metadata = self._get_ia_metadata()
            if ia_metadata:
                # Find database file info
                for file_info in ia_metadata.get("files", []):
                    if file_info.get("name") == self.ia_database_filename:
                        status["ia_file_info"] = file_info
                        break

                status["ia_metadata"] = ia_metadata.get("metadata", {})

        return status

    def smart_sync(self, prefer_local: bool = True, wait_for_lock: bool = True) -> str:
        """Intelligent sync based on modification times and existence."""

        # Check for lock first
        lock_metadata = self._check_lock_exists()
        if lock_metadata:
            if wait_for_lock:
                self.logger.info("Database is locked, waiting for release...")
                if not self._wait_for_lock_release():
                    return "lock_timeout"
            else:
                return "locked"

        local_exists = self.local_db_path.exists()
        ia_exists = self.database_exists_in_ia()

        if not local_exists and not ia_exists:
            return "no_database_found"

        if local_exists and not ia_exists:
            self.logger.info(
                "Local database exists, IA database missing - uploading to IA"
            )
            success = self.upload_database_to_ia()
            return "uploaded_to_ia" if success else "upload_failed"

        if not local_exists and ia_exists:
            self.logger.info("IA database exists, local missing - downloading from IA")
            success = self.download_database_from_ia()
            return "downloaded_from_ia" if success else "download_failed"

        # Both exist - need to decide which is newer
        sync_metadata = self._get_sync_metadata()
        local_metadata = self._get_local_metadata()

        # If we have sync metadata, use it to make smart decisions
        if sync_metadata.get("sha256") == local_metadata["sha256"]:
            ia_file_info = self._get_ia_db_file_info()
            ia_mtime = None
            if ia_file_info:
                try:
                    ia_mtime = float(ia_file_info.get("mtime", 0))
                except (TypeError, ValueError):
                    ia_mtime = None

            local_mtime = local_metadata.get("modified_time")

            if ia_mtime and local_mtime and ia_mtime > local_mtime:
                self.logger.info("IA database updated since last sync - downloading")
                success = self.download_database_from_ia(force=True)
                return "downloaded_from_ia" if success else "download_failed"

            self.logger.info("Local database unchanged since last sync")
            return "already_synced"
        ia_file_info = self._get_ia_db_file_info()
        ia_mtime = None
        if ia_file_info:
            try:
                ia_mtime = float(ia_file_info.get("mtime", 0))
            except (TypeError, ValueError):
                ia_mtime = None

        local_mtime = local_metadata.get("modified_time")

        if ia_mtime and local_mtime:
            if ia_mtime > local_mtime:
                self.logger.info("IA database is newer - downloading")
                success = self.download_database_from_ia(force=True)
                return "downloaded_from_ia" if success else "download_failed"

        # Local has changes - upload to IA (assuming local is authoritative for development)
        if prefer_local or not ia_mtime or (local_mtime and local_mtime >= ia_mtime):
            self.logger.info("Local database has changes - uploading to IA")
            success = self.upload_database_to_ia()
            return "uploaded_to_ia" if success else "upload_failed"
        else:
            self.logger.info("Downloading latest from IA")
            success = self.download_database_from_ia(force=True)
            return "downloaded_from_ia" if success else "download_failed"

    def export_and_upload_parquet_datasets(
        self,
        tables: Optional[list] = None,
        collection: str = "opensource",
        wait_for_lock: bool = True,
        cleanup_files: bool = True,
    ) -> Dict[str, Any]:
        """
        Export tables from DuckDB to Parquet files and upload to Internet Archive.
        
        Args:
            tables: List of table names to export. If None, exports all tables.
            collection: IA collection to upload to (default: "opensource")
            wait_for_lock: Whether to wait for database lock release
            cleanup_files: Whether to clean up temporary Parquet files after upload
            
        Returns:
            Dict with export results and upload status for each table
        """
        if not self.local_db_path.exists():
            self.logger.error("Local database not found")
            return {"error": "Local database not found"}

        # Check for existing lock
        lock_metadata = self._check_lock_exists()
        if lock_metadata:
            if wait_for_lock:
                self.logger.info("Database is locked, waiting for release...")
                if not self._wait_for_lock_release():
                    return {"error": "Lock timeout"}
            else:
                return {"error": "Database is locked by another operation"}

        # Create lock for export operation
        if not self._create_lock("parquet_export", timeout_minutes=90):
            self.logger.error("Failed to create lock for export operation")
            return {"error": "Failed to create lock for export operation"}

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tables_exported": [],
            "tables_failed": [],
            "upload_results": {},
            "total_files_created": 0,
            "total_files_uploaded": 0,
        }

        temp_files = []  # Track temporary files for cleanup

        try:
            # Connect to DuckDB
            self.logger.info("Connecting to DuckDB database")
            with duckdb.connect(str(self.local_db_path)) as conn:
                
                # Get list of tables if not provided
                if tables is None:
                    table_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                    tables = [row[0] for row in conn.execute(table_query).fetchall()]
                    self.logger.info(f"Found {len(tables)} tables in database")
                else:
                    self.logger.info(f"Exporting {len(tables)} specified tables")

                if not tables:
                    self.logger.warning("No tables found to export")
                    return {"error": "No tables found to export"}

                # Create temporary directory for parquet files
                temp_dir = Path(tempfile.mkdtemp(prefix="causaganha_parquet_"))
                self.logger.info(f"Created temporary directory: {temp_dir}")

                # Export each table to Parquet
                for table_name in tables:
                    try:
                        self.logger.info(f"Exporting table: {table_name}")
                        
                        # Create timestamp for filename versioning
                        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                        parquet_filename = f"{table_name}_{timestamp}.parquet"
                        parquet_path = temp_dir / parquet_filename
                        
                        # Check if table exists and has data
                        count_query = f"SELECT COUNT(*) FROM {table_name}"
                        row_count = conn.execute(count_query).fetchone()[0]
                        
                        if row_count == 0:
                            self.logger.warning(f"Table {table_name} is empty, skipping")
                            continue
                            
                        self.logger.info(f"Table {table_name} has {row_count:,} rows")
                        
                        # Export table to Parquet using DuckDB's COPY command
                        copy_query = f"COPY {table_name} TO '{parquet_path}' (FORMAT 'parquet')"
                        conn.execute(copy_query)
                        
                        # Verify file was created
                        if not parquet_path.exists():
                            raise Exception(f"Parquet file was not created: {parquet_path}")
                            
                        file_size = parquet_path.stat().st_size
                        self.logger.info(f"✅ Exported {table_name} to {parquet_filename} ({file_size:,} bytes)")
                        
                        temp_files.append(parquet_path)
                        results["tables_exported"].append(table_name)
                        results["total_files_created"] += 1
                        
                    except Exception as e:
                        self.logger.error(f"❌ Failed to export table {table_name}: {e}")
                        results["tables_failed"].append({"table": table_name, "error": str(e)})
                        continue

                # Upload each Parquet file to Internet Archive
                self.logger.info(f"Uploading {len(temp_files)} Parquet files to Internet Archive")
                
                for parquet_path in temp_files:
                    try:
                        table_name = parquet_path.name.split('_')[0]  # Extract table name from filename
                        
                        # Create unique IA identifier for this dataset
                        ia_identifier = f"causaganha-dataset-{table_name}"
                        
                        # Calculate file hash
                        file_hash = self._calculate_file_hash(parquet_path)
                        file_size = parquet_path.stat().st_size
                        
                        # Prepare metadata for IA upload
                        upload_metadata = {
                            "title": f"CausaGanha Dataset - {table_name}",
                            "description": f"Parquet dataset export from CausaGanha database table '{table_name}'. "
                                         f"Contains judicial analysis data exported on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC.",
                            "creator": "CausaGanha System",
                            "subject": f"database; judicial; legal; parquet; dataset; {table_name}; causaganha",
                            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            "language": "por",
                            "collection": collection,
                            "mediatype": "data",
                            "file_size": str(file_size),
                            "sha256": file_hash,
                            "export_timestamp": datetime.now(timezone.utc).isoformat(),
                            "source_table": table_name,
                            "format": "parquet",
                            "database_version": "1.0",
                            "causaganha_version": "1.0",
                        }
                        
                        # Build IA upload command
                        cmd = ["ia", "upload", ia_identifier, str(parquet_path)]
                        
                        # Add metadata
                        for key, value in upload_metadata.items():
                            cmd.extend([f"--metadata={key}:{value}"])
                        
                        self.logger.info(f"Uploading {parquet_path.name} to IA identifier: {ia_identifier}")
                        
                        # Execute upload with extended timeout for large files
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                        
                        if result.returncode == 0:
                            ia_url = f"https://archive.org/details/{ia_identifier}"
                            self.logger.info(f"✅ Successfully uploaded {parquet_path.name} to {ia_url}")
                            
                            results["upload_results"][table_name] = {
                                "success": True,
                                "ia_identifier": ia_identifier,
                                "ia_url": ia_url,
                                "file_size": file_size,
                                "sha256": file_hash,
                                "filename": parquet_path.name,
                            }
                            results["total_files_uploaded"] += 1
                            
                        else:
                            error_msg = f"IA upload failed: {result.stderr}"
                            self.logger.error(f"❌ Failed to upload {parquet_path.name}: {error_msg}")
                            
                            results["upload_results"][table_name] = {
                                "success": False,
                                "error": error_msg,
                                "filename": parquet_path.name,
                            }
                            
                    except Exception as e:
                        error_msg = f"Upload error: {e}"
                        self.logger.error(f"❌ Failed to upload {parquet_path.name}: {error_msg}")
                        
                        results["upload_results"][table_name] = {
                            "success": False,
                            "error": error_msg,
                            "filename": parquet_path.name,
                        }

                # Clean up temporary files if requested
                if cleanup_files:
                    self.logger.info("Cleaning up temporary Parquet files")
                    try:
                        shutil.rmtree(temp_dir)
                        self.logger.info(f"✅ Cleaned up temporary directory: {temp_dir}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clean up temporary directory: {e}")
                else:
                    self.logger.info(f"Temporary files kept in: {temp_dir}")
                    results["temp_directory"] = str(temp_dir)

        except Exception as e:
            self.logger.error(f"Export operation failed: {e}")
            results["error"] = str(e)
            
            # Clean up temporary files on error
            if cleanup_files:
                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except Exception as cleanup_error:
                        self.logger.warning(f"Failed to clean up {temp_file}: {cleanup_error}")

        finally:
            # Always remove the lock
            self._remove_lock()

        # Log final results
        exported_count = len(results["tables_exported"])
        failed_count = len(results["tables_failed"])
        uploaded_count = results["total_files_uploaded"]
        
        if exported_count > 0:
            self.logger.info(f"📊 Export Summary:")
            self.logger.info(f"  • Tables exported: {exported_count}")
            self.logger.info(f"  • Tables failed: {failed_count}")
            self.logger.info(f"  • Files uploaded to IA: {uploaded_count}")
            
            if uploaded_count > 0:
                self.logger.info(f"  • All datasets available at: https://archive.org/search.php?query=creator%3A%22CausaGanha%20System%22")
        
        return results


def main():
    """CLI interface for database sync."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync CausaGanha database with Internet Archive"
    )
    parser.add_argument(
        "action",
        choices=["status", "download", "upload", "sync", "export-parquet"],
        help="Action to perform",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force operation even if not needed"
    )
    parser.add_argument(
        "--prefer-ia", action="store_true", help="Prefer IA version in smart sync"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Specific tables to export (for export-parquet action)",
    )
    parser.add_argument(
        "--collection",
        default="opensource",
        help="IA collection to upload to (default: opensource)",
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep temporary Parquet files after upload",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    sync = IADatabaseSync()

    if args.action == "status":
        status = sync.sync_status()
        print(json.dumps(status, indent=2, default=str))

    elif args.action == "download":
        success = sync.download_database_from_ia(force=args.force)
        exit(0 if success else 1)

    elif args.action == "upload":
        success = sync.upload_database_to_ia(force=args.force)
        exit(0 if success else 1)

    elif args.action == "sync":
        result = sync.smart_sync(
            prefer_local=not args.prefer_ia, wait_for_lock=not args.force
        )
        print(f"Sync result: {result}")

        if result in [
            "upload_failed",
            "download_failed",
            "no_database_found",
            "lock_timeout",
        ]:
            exit(1)
        elif result == "locked":
            print(
                "Database is locked by another operation. Use --force to skip waiting."
            )
            exit(1)

    elif args.action == "export-parquet":
        result = sync.export_and_upload_parquet_datasets(
            tables=args.tables,
            collection=args.collection,
            wait_for_lock=not args.force,
            cleanup_files=not args.keep_files,
        )
        
        print(json.dumps(result, indent=2, default=str))
        
        if "error" in result:
            exit(1)
        elif result["total_files_uploaded"] == 0:
            print("No files were successfully uploaded")
            exit(1)


if __name__ == "__main__":
    main()
