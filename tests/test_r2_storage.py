# causaganha/tests/test_r2_storage.py
"""
Tests for Cloudflare R2 storage integration.

Uses mocking to avoid requiring actual R2 credentials during testing.
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add src directory to sys.path to allow importing causaganha
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from r2_storage import CloudflareR2Storage, R2Config
from r2_queries import R2DuckDBClient, R2QueryConfig


class TestR2Config:
    """Test R2 configuration."""

    def test_r2_config_creation(self):
        config = R2Config(
            account_id="test-account",
            access_key_id="test-key",
            secret_access_key="test-secret",
        )

        assert config.account_id == "test-account"
        assert config.bucket_name == "causa-ganha"  # default
        assert config.endpoint_url == "https://test-account.r2.cloudflarestorage.com"

    def test_r2_config_custom_bucket(self):
        config = R2Config(
            account_id="test-account",
            access_key_id="test-key",
            secret_access_key="test-secret",
            bucket_name="custom-bucket",
        )

        assert config.bucket_name == "custom-bucket"


class TestCloudflareR2Storage:
    """Test R2 storage operations with mocked AWS calls."""

    @pytest.fixture
    def mock_config(self):
        return R2Config(
            account_id="test-account",
            access_key_id="test-key",
            secret_access_key="test-secret",
        )

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_db_file(self, temp_dir):
        """Create sample database file."""
        db_file = temp_dir / "test.duckdb"
        db_file.write_bytes(b"fake database content for testing")
        return db_file

    @patch("r2_storage.boto3.client")
    def test_r2_storage_initialization(self, mock_boto3, mock_config):
        """Test R2 storage client initialization."""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        storage = CloudflareR2Storage(mock_config)

        assert storage.config == mock_config
        assert storage.s3_client == mock_s3_client

        # Verify boto3 client was called with correct parameters
        mock_boto3.assert_called_once_with(
            "s3",
            endpoint_url=mock_config.endpoint_url,
            aws_access_key_id=mock_config.access_key_id,
            aws_secret_access_key=mock_config.secret_access_key,
            region_name=mock_config.region,
        )

    @patch.dict(
        "os.environ",
        {
            "CLOUDFLARE_ACCOUNT_ID": "env-account",
            "CLOUDFLARE_R2_ACCESS_KEY_ID": "env-key",
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY": "env-secret",
            "CLOUDFLARE_R2_BUCKET": "env-bucket",
        },
    )
    @patch("r2_storage.boto3.client")
    def test_from_env_creation(self, mock_boto3):
        """Test creating R2 storage from environment variables."""
        mock_boto3.return_value = Mock()

        storage = CloudflareR2Storage.from_env()

        assert storage.config.account_id == "env-account"
        assert storage.config.access_key_id == "env-key"
        assert storage.config.secret_access_key == "env-secret"
        assert storage.config.bucket_name == "env-bucket"

    @patch("r2_storage.boto3.client")
    def test_ensure_bucket_exists(self, mock_boto3, mock_config):
        """Test bucket existence check."""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        # Mock successful head_bucket call
        mock_s3_client.head_bucket.return_value = {}

        storage = CloudflareR2Storage(mock_config)
        result = storage.ensure_bucket()

        assert result is True
        mock_s3_client.head_bucket.assert_called_once_with(
            Bucket=mock_config.bucket_name
        )

    @patch("r2_storage.boto3.client")
    def test_ensure_bucket_creates_if_missing(self, mock_boto3, mock_config):
        """Test bucket creation when it doesn't exist."""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        # Mock bucket doesn't exist
        from botocore.exceptions import ClientError

        mock_s3_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadBucket"
        )
        mock_s3_client.create_bucket.return_value = {}

        storage = CloudflareR2Storage(mock_config)
        result = storage.ensure_bucket()

        assert result is True
        mock_s3_client.create_bucket.assert_called_once_with(
            Bucket=mock_config.bucket_name
        )

    def test_file_hash_calculation(self, sample_db_file):
        """Test SHA-256 hash calculation."""
        # We can test this without mocking since it's pure file I/O
        config = R2Config("test", "test", "test")

        with patch("r2_storage.boto3.client"):
            storage = CloudflareR2Storage(config)
            file_hash = storage.calculate_file_hash(sample_db_file)

        assert len(file_hash) == 64  # SHA-256 hex length
        assert isinstance(file_hash, str)

    def test_file_compression(self, sample_db_file, temp_dir):
        """Test zstandard compression."""
        config = R2Config("test", "test", "test")
        output_path = temp_dir / "compressed.zst"

        with patch("r2_storage.boto3.client"):
            storage = CloudflareR2Storage(config)
            compressed_path = storage.compress_file(sample_db_file, output_path)

        assert compressed_path == output_path
        assert output_path.exists()
        assert output_path.stat().st_size < sample_db_file.stat().st_size

    def test_file_decompression(self, temp_dir):
        """Test zstandard decompression."""
        config = R2Config("test", "test", "test")

        # Create a simple compressed file
        original_content = b"test content for compression"
        original_file = temp_dir / "original.txt"
        original_file.write_bytes(original_content)

        with patch("r2_storage.boto3.client"):
            storage = CloudflareR2Storage(config)

            # Compress
            compressed_path = storage.compress_file(original_file)

            # Decompress
            decompressed_path = storage.decompress_file(compressed_path)

            # Verify content matches
            assert decompressed_path.read_bytes() == original_content

    @patch("r2_storage.boto3.client")
    @patch("r2_storage.CausaGanhaDB")
    def test_create_duckdb_snapshot(
        self, mock_db_class, mock_boto3, mock_config, temp_dir
    ):
        """Test DuckDB snapshot creation."""
        # Mock database operations
        mock_db = Mock()
        mock_db.conn.execute.return_value = None
        mock_db.get_statistics.return_value = {
            "total_decisoes": 100,
            "total_advogados": 50,
        }
        mock_db_class.return_value.__enter__.return_value = mock_db

        mock_boto3.return_value = Mock()

        storage = CloudflareR2Storage(mock_config)

        # Create fake database file
        db_path = temp_dir / "test.duckdb"
        db_path.write_bytes(b"fake db")

        # Override compression to avoid actual zstd operations in test
        with patch.object(storage, "compress_file") as mock_compress:
            mock_compress.return_value = temp_dir / "snapshot.duckdb.zst"

            result = storage.create_duckdb_snapshot(db_path, temp_dir)

            assert result == temp_dir / "snapshot.duckdb.zst"
            mock_compress.assert_called_once()

    @patch("r2_storage.boto3.client")
    def test_upload_snapshot(self, mock_boto3, mock_config, sample_db_file):
        """Test snapshot upload to R2."""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        # Mock successful upload and head_object response
        mock_s3_client.upload_file.return_value = None
        mock_s3_client.head_object.return_value = {
            "ETag": '"test-etag"',
            "ContentLength": 1024,
        }

        storage = CloudflareR2Storage(mock_config)
        result = storage.upload_snapshot(sample_db_file)

        assert "bucket" in result
        assert "s3_key" in result
        assert "size_bytes" in result
        assert "sha256" in result

        # Verify upload was called
        mock_s3_client.upload_file.assert_called_once()

    @patch("r2_storage.boto3.client")
    def test_list_snapshots(self, mock_boto3, mock_config):
        """Test listing snapshots from R2."""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "snapshots/test1.duckdb.zst",
                    "Size": 1024,
                    "LastModified": datetime.now(),
                    "ETag": '"etag1"',
                }
            ]
        }

        # Mock head_object for metadata
        mock_s3_client.head_object.return_value = {"Metadata": {"sha256": "test-hash"}}

        storage = CloudflareR2Storage(mock_config)
        snapshots = storage.list_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0]["key"] == "snapshots/test1.duckdb.zst"
        assert "metadata" in snapshots[0]

    @patch("r2_storage.boto3.client")
    def test_cleanup_old_snapshots(self, mock_boto3, mock_config):
        """Test cleanup of old snapshots."""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        # Mock old snapshot
        old_date = datetime.now() - timedelta(days=35)
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "snapshots/old.duckdb.zst",
                    "Size": 1024,
                    "LastModified": old_date,
                    "ETag": '"old-etag"',
                }
            ]
        }

        mock_s3_client.head_object.return_value = {"Metadata": {}}
        mock_s3_client.delete_object.return_value = {}

        storage = CloudflareR2Storage(mock_config)
        deleted_count = storage.cleanup_old_snapshots(retention_days=30)

        assert deleted_count == 1
        mock_s3_client.delete_object.assert_called_once()


class TestR2DuckDBClient:
    """Test remote DuckDB queries against R2."""

    @pytest.fixture
    def mock_query_config(self):
        return R2QueryConfig(
            account_id="test-account",
            access_key_id="test-key",
            secret_access_key="test-secret",
        )

    @patch("r2_queries.duckdb.connect")
    @patch("r2_queries.CloudflareR2Storage")
    def test_r2_client_initialization(
        self, mock_r2_storage, mock_duckdb_connect, mock_query_config
    ):
        """Test R2 DuckDB client initialization."""
        mock_conn = Mock()
        mock_duckdb_connect.return_value = mock_conn
        mock_r2_storage.return_value = Mock()

        client = R2DuckDBClient(mock_query_config)

        assert client.config == mock_query_config
        assert client.conn == mock_conn

        # Verify S3 configuration was set
        mock_conn.execute.assert_called()

    @patch("r2_queries.duckdb.connect")
    @patch("r2_queries.CloudflareR2Storage")
    def test_get_snapshot_s3_url(
        self, mock_r2_storage, mock_duckdb_connect, mock_query_config
    ):
        """Test S3 URL generation."""
        mock_duckdb_connect.return_value = Mock()
        mock_r2_storage.return_value = Mock()

        client = R2DuckDBClient(mock_query_config)
        url = client.get_snapshot_s3_url("snapshots/test.duckdb")

        assert url == "s3://causa-ganha/snapshots/test.duckdb"

    @patch.dict(
        "os.environ",
        {
            "CLOUDFLARE_ACCOUNT_ID": "env-account",
            "CLOUDFLARE_R2_ACCESS_KEY_ID": "env-key",
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY": "env-secret",
        },
    )
    @patch("r2_queries.duckdb.connect")
    @patch("r2_queries.CloudflareR2Storage")
    def test_from_env_creation(self, mock_r2_storage, mock_duckdb_connect):
        """Test creating R2 client from environment."""
        mock_duckdb_connect.return_value = Mock()
        mock_r2_storage.return_value = Mock()

        client = R2DuckDBClient.from_env()

        assert client.config.account_id == "env-account"


if __name__ == "__main__":
    pytest.main([__file__])
