import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


# Add repo root to path
sys.path.append(os.getcwd())

# We import the module, but functions might change signature
from scripts.pipeline.collect import upload_to_ia


class TestUploadBoto(unittest.TestCase):
    def setUp(self):
        self.item_id = "djen-2024-01-01"
        self.file_path = Path("test.zip")
        self.date_str = "2024-01-01"
        self.content = b"fake-zip-content"

    @patch("scripts.pipeline.collect._compute_md5")
    def test_upload_to_ia_success(self, mock_md5):
        mock_md5.return_value = "d41d8cd98f00b204e9800998ecf8427e"

        mock_s3 = MagicMock()

        # Mock file open
        with patch("pathlib.Path.open", mock_open(read_data=self.content)):
            success = upload_to_ia(mock_s3, self.item_id, self.file_path, self.date_str)

        assert success

        # Verify put_object called
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        assert call_args is not None

        kwargs = call_args[1]
        assert kwargs["Bucket"] == self.item_id
        assert kwargs["Key"] == self.file_path.name

        # Check metadata/headers are passed
        # Note: IA headers like x-archive-auto-make-bucket are handled via event hooks in the client,
        # so they won't appear in put_object arguments directly, but Metadata will.
        assert "Metadata" in kwargs
        metadata = kwargs["Metadata"]
        assert metadata["collection"] == "opensource"
        assert metadata["mediatype"] == "data"
        assert metadata["title"] == f"DJEN Data - {self.date_str}"

    @patch("scripts.pipeline.collect._compute_md5")
    def test_upload_to_ia_failure(self, mock_md5):
        mock_md5.return_value = "d41d8cd98f00b204e9800998ecf8427e"
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 Error")

        with patch("pathlib.Path.open", mock_open(read_data=self.content)):
            success = upload_to_ia(mock_s3, self.item_id, self.file_path, self.date_str)

        assert not success
