# causaganha/core/r2_storage.py
"""
Cloudflare R2 Storage integration for CausaGanha.

Provides unified storage for DuckDB snapshots, PDF backups, and data archival
using Cloudflare R2 with S3-compatible API via boto3.
"""

import boto3
import json
import hashlib
import zstandard as zstd
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from botocore.exceptions import ClientError, NoCredentialsError
import os

from .database import CausaGanhaDB

logger = logging.getLogger(__name__)


@dataclass
class R2Config:
    """Configuration for Cloudflare R2 storage."""
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str = "causa-ganha"
    region: str = "auto"  # R2 uses "auto" region
    
    @property
    def endpoint_url(self) -> str:
        """Generate R2 endpoint URL."""
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


class CloudflareR2Storage:
    """
    Cloudflare R2 storage manager for CausaGanha data.
    
    Features:
    - DuckDB snapshot compression and upload
    - PDF archival with metadata tracking
    - Automatic snapshot rotation (30 days retention)
    - S3-compatible API via boto3
    - Cost-optimized storage strategies
    """
    
    def __init__(self, config: R2Config):
        self.config = config
        self.s3_client = None
        self._connect()
        
    def _connect(self):
        """Initialize S3 client for R2."""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name=self.config.region
            )
            logger.info(f"Connected to Cloudflare R2: {self.config.bucket_name}")
            
        except NoCredentialsError:
            logger.error("R2 credentials not found. Set CLOUDFLARE_* environment variables.")
            raise
        except (ValueError, ConnectionError, RuntimeError) as e:
            logger.error("Failed to connect to R2: %s", e)
            raise
    
    @classmethod
    def from_env(cls) -> 'CloudflareR2Storage':
        """Create R2Storage from environment variables."""
        config = R2Config(
            account_id=os.getenv('CLOUDFLARE_ACCOUNT_ID'),
            access_key_id=os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID'), 
            secret_access_key=os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY'),
            bucket_name=os.getenv('CLOUDFLARE_R2_BUCKET', 'causa-ganha')
        )
        
        # Validate required fields
        if not all([config.account_id, config.access_key_id, config.secret_access_key]):
            raise ValueError("Missing required R2 environment variables")
            
        return cls(config)
    
    def ensure_bucket(self) -> bool:
        """Ensure bucket exists, create if not."""
        try:
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            logger.info(f"Bucket {self.config.bucket_name} exists")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    self.s3_client.create_bucket(Bucket=self.config.bucket_name)
                    logger.info(f"Created bucket: {self.config.bucket_name}")
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def compress_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Compress file using zstandard with high compression.
        
        Args:
            input_path: Path to input file
            output_path: Path for compressed output (optional)
            
        Returns:
            Path to compressed file
        """
        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + '.zst')
        
        logger.info(f"Compressing {input_path} -> {output_path}")
        
        # Use high compression level for storage efficiency
        cctx = zstd.ZstdCompressor(level=19, threads=-1)
        
        with open(input_path, 'rb') as infile:
            with open(output_path, 'wb') as outfile:
                cctx.copy_stream(infile, outfile)
        
        # Log compression stats
        original_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        ratio = compressed_size / original_size
        
        logger.info(f"Compression: {original_size:,} -> {compressed_size:,} bytes ({ratio:.1%})")
        
        return output_path
    
    def decompress_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """Decompress zstandard compressed file."""
        if output_path is None:
            output_path = input_path.with_suffix('')  # Remove .zst extension
        
        logger.info(f"Decompressing {input_path} -> {output_path}")
        
        dctx = zstd.ZstdDecompressor()
        
        with open(input_path, 'rb') as infile:
            with open(output_path, 'wb') as outfile:
                dctx.copy_stream(infile, outfile)
        
        return output_path
    
    def create_duckdb_snapshot(self, 
                              db_path: Path = Path("data/causaganha.duckdb"),
                              snapshot_dir: Path = Path("data/snapshots")) -> Path:
        """
        Create compressed DuckDB snapshot.
        
        Args:
            db_path: Path to DuckDB database
            snapshot_dir: Directory for snapshots
            
        Returns:
            Path to compressed snapshot
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"causaganha_{timestamp}.duckdb"
        
        snapshot_dir.mkdir(exist_ok=True)
        snapshot_path = snapshot_dir / snapshot_name
        
        # Create snapshot by copying database
        logger.info(f"Creating DuckDB snapshot: {snapshot_path}")
        
        # Use DuckDB COPY command for consistent snapshot
        with CausaGanhaDB(db_path) as db:
            # Export to new database file 
            db.conn.execute(f"EXPORT DATABASE '{snapshot_path}' (FORMAT DUCKDB)")
            
            # Get database statistics
            stats = db.get_statistics()
            logger.info(f"Snapshot created with {stats.get('total_decisoes', 0)} decisions, "
                       f"{stats.get('total_advogados', 0)} lawyers")
        
        # Compress snapshot
        compressed_path = self.compress_file(snapshot_path)
        
        # Remove uncompressed snapshot
        snapshot_path.unlink()
        
        return compressed_path
    
    def upload_snapshot(self, snapshot_path: Path, 
                       s3_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload compressed snapshot to R2.
        
        Args:
            snapshot_path: Path to compressed snapshot
            s3_key: S3 key (optional, derived from filename)
            
        Returns:
            Upload metadata
        """
        if s3_key is None:
            s3_key = f"snapshots/{snapshot_path.name}"
        
        # Calculate metadata
        file_size = snapshot_path.stat().st_size
        file_hash = self.calculate_file_hash(snapshot_path)
        
        metadata = {
            'sha256': file_hash,
            'original_size': str(file_size),
            'compression': 'zstd',
            'created_at': datetime.now().isoformat(),
            'source': 'causaganha-pipeline'
        }
        
        logger.info(f"Uploading snapshot to R2: {s3_key} ({file_size:,} bytes)")
        
        try:
            self.s3_client.upload_file(
                str(snapshot_path),
                self.config.bucket_name,
                s3_key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ContentType': 'application/octet-stream'
                }
            )
            
            # Get object metadata for verification
            response = self.s3_client.head_object(Bucket=self.config.bucket_name, Key=s3_key)
            
            result = {
                'bucket': self.config.bucket_name,
                's3_key': s3_key,
                'size_bytes': file_size,
                'sha256': file_hash,
                'upload_time': datetime.now().isoformat(),
                'etag': response['ETag'].strip('"'),
                'metadata': metadata
            }
            
            logger.info(f"✅ Snapshot uploaded successfully: {s3_key}")
            return result
            
        except ClientError as e:
            logger.error(f"Failed to upload snapshot: {e}")
            raise
    
    def list_snapshots(self, prefix: str = "snapshots/") -> List[Dict[str, Any]]:
        """List all snapshots in R2."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            snapshots = []
            for obj in response.get('Contents', []):
                # Get object metadata
                head_response = self.s3_client.head_object(
                    Bucket=self.config.bucket_name,
                    Key=obj['Key']
                )
                
                snapshot_info = {
                    'key': obj['Key'],
                    'size_bytes': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"'),
                    'metadata': head_response.get('Metadata', {})
                }
                snapshots.append(snapshot_info)
            
            # Sort by last modified (newest first)
            snapshots.sort(key=lambda x: x['last_modified'], reverse=True)
            
            logger.info(f"Found {len(snapshots)} snapshots in R2")
            return snapshots
            
        except ClientError as e:
            logger.error(f"Failed to list snapshots: {e}")
            return []
    
    def download_snapshot(self, s3_key: str, 
                         local_path: Optional[Path] = None) -> Path:
        """
        Download and decompress snapshot from R2.
        
        Args:
            s3_key: S3 key of snapshot
            local_path: Local path for download (optional)
            
        Returns:
            Path to decompressed database
        """
        if local_path is None:
            local_path = Path("data/snapshots") / Path(s3_key).name
        
        local_path.parent.mkdir(exist_ok=True)
        
        logger.info(f"Downloading snapshot: {s3_key} -> {local_path}")
        
        try:
            self.s3_client.download_file(
                self.config.bucket_name,
                s3_key, 
                str(local_path)
            )
            
            # Decompress if it's a .zst file
            if local_path.suffix == '.zst':
                decompressed_path = self.decompress_file(local_path)
                local_path.unlink()  # Remove compressed file
                return decompressed_path
            
            return local_path
            
        except ClientError as e:
            logger.error(f"Failed to download snapshot: {e}")
            raise
    
    def cleanup_old_snapshots(self, retention_days: int = 30) -> int:
        """
        Remove snapshots older than retention period.
        
        Args:
            retention_days: Number of days to retain snapshots
            
        Returns:
            Number of snapshots deleted
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        snapshots = self.list_snapshots()
        
        deleted_count = 0
        for snapshot in snapshots:
            snapshot_date = datetime.fromisoformat(snapshot['last_modified'].replace('Z', '+00:00'))
            
            if snapshot_date < cutoff_date:
                logger.info(f"Deleting old snapshot: {snapshot['key']} "
                           f"(age: {(datetime.now() - snapshot_date.replace(tzinfo=None)).days} days)")
                
                try:
                    self.s3_client.delete_object(
                        Bucket=self.config.bucket_name,
                        Key=snapshot['key']
                    )
                    deleted_count += 1
                    
                except ClientError as e:
                    logger.error(f"Failed to delete snapshot {snapshot['key']}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old snapshots")
        return deleted_count
    
    def backup_database(self, 
                       db_path: Path = Path("data/causaganha.duckdb"),
                       cleanup_old: bool = True) -> Dict[str, Any]:
        """
        Complete database backup workflow.
        
        Args:
            db_path: Path to DuckDB database
            cleanup_old: Whether to cleanup old snapshots
            
        Returns:
            Backup result metadata
        """
        logger.info("🚀 Starting database backup to Cloudflare R2")
        
        # Ensure bucket exists
        if not self.ensure_bucket():
            raise RuntimeError("Failed to ensure R2 bucket exists")
        
        # Create compressed snapshot
        snapshot_path = self.create_duckdb_snapshot(db_path)
        
        try:
            # Upload to R2
            upload_result = self.upload_snapshot(snapshot_path)
            
            # Cleanup old snapshots if requested
            if cleanup_old:
                deleted_count = self.cleanup_old_snapshots()
                upload_result['cleanup'] = {'deleted_snapshots': deleted_count}
            
            # Get current snapshot count
            snapshots = self.list_snapshots()
            upload_result['total_snapshots'] = len(snapshots)
            
            return upload_result
            
        finally:
            # Always cleanup local snapshot
            if snapshot_path.exists():
                snapshot_path.unlink()
                logger.info(f"Cleaned up local snapshot: {snapshot_path}")
    
    def get_latest_snapshot_key(self) -> Optional[str]:
        """Get S3 key of the most recent snapshot."""
        snapshots = self.list_snapshots()
        if snapshots:
            return snapshots[0]['key']  # Already sorted by date (newest first)
        return None
    
    def restore_database(self, 
                        target_path: Path = Path("data/causaganha_restored.duckdb"),
                        snapshot_key: Optional[str] = None) -> Path:
        """
        Restore database from R2 snapshot.
        
        Args:
            target_path: Where to restore database
            snapshot_key: Specific snapshot to restore (latest if None)
            
        Returns:
            Path to restored database
        """
        if snapshot_key is None:
            snapshot_key = self.get_latest_snapshot_key()
            if not snapshot_key:
                raise ValueError("No snapshots found in R2")
        
        logger.info(f"Restoring database from snapshot: {snapshot_key}")
        
        # Download and decompress
        restored_path = self.download_snapshot(snapshot_key, target_path)
        
        logger.info(f"✅ Database restored to: {restored_path}")
        return restored_path


def main():
    """CLI interface for R2 storage operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cloudflare R2 storage operations')
    parser.add_argument('action', choices=['backup', 'list', 'restore', 'cleanup'], 
                       help='Action to perform')
    parser.add_argument('--db-path', type=Path, default=Path('data/causaganha.duckdb'),
                       help='Path to DuckDB database')
    parser.add_argument('--snapshot-key', help='Specific snapshot key for restore')
    parser.add_argument('--retention-days', type=int, default=30,
                       help='Days to retain snapshots for cleanup')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize R2 storage
        r2_storage = CloudflareR2Storage.from_env()
        
        if args.action == 'backup':
            result = r2_storage.backup_database(args.db_path)
            print(f"✅ Backup completed: {result['s3_key']}")
            print(f"   Size: {result['size_bytes']:,} bytes")
            print(f"   Total snapshots: {result['total_snapshots']}")
            
        elif args.action == 'list':
            snapshots = r2_storage.list_snapshots()
            print(f"📦 Found {len(snapshots)} snapshots:")
            for snapshot in snapshots:
                print(f"   {snapshot['key']} - {snapshot['size_bytes']:,} bytes - {snapshot['last_modified']}")
                
        elif args.action == 'restore':
            restored_path = r2_storage.restore_database(
                target_path=Path('data/causaganha_restored.duckdb'),
                snapshot_key=args.snapshot_key
            )
            print(f"✅ Database restored to: {restored_path}")
            
        elif args.action == 'cleanup':
            deleted_count = r2_storage.cleanup_old_snapshots(args.retention_days)
            print(f"🧹 Cleaned up {deleted_count} old snapshots")
            
    except (OSError, RuntimeError, ValueError, ConnectionError) as e:
        logger.error("Operation failed: %s", e)
        exit(1)


if __name__ == "__main__":
    main()