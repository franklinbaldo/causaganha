import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError

# Add repository root to path
sys.path.append(os.getcwd())

from scripts.pipeline.collect import upload_to_ia

@patch("scripts.pipeline.collect._get_ia_credentials")
@patch("boto3.client")
def test_upload_to_ia_success(mock_boto_client, mock_creds, tmp_path):
    # Setup
    mock_creds.return_value = ("access", "secret")

    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    # Create dummy file
    file_path = tmp_path / "test.zip"
    file_path.write_text("dummy content")

    # Run
    result = upload_to_ia("bucket-id", file_path, "2024-01-01")

    # Verify
    assert result is True

    # Check client creation
    mock_boto_client.assert_called_once()
    call_args = mock_boto_client.call_args
    assert call_args[0] == ("s3",)
    assert call_args[1]["endpoint_url"] == "https://s3.us.archive.org"
    assert call_args[1]["aws_access_key_id"] == "access"
    assert call_args[1]["aws_secret_access_key"] == "secret"
    assert call_args[1]["config"].retries["max_attempts"] == 10
    assert call_args[1]["config"].retries["mode"] == "adaptive"

    # Check event registration
    mock_s3.meta.events.register.assert_called_once()
    event_name, handler = mock_s3.meta.events.register.call_args[0]
    assert event_name == "before-call:s3:PutObject"

    # Check put_object call
    mock_s3.put_object.assert_called_once()
    kwargs = mock_s3.put_object.call_args[1]
    assert kwargs["Bucket"] == "bucket-id"
    assert kwargs["Key"] == "test.zip"
    assert "Body" in kwargs
    assert kwargs["Metadata"]["title"] == "DJEN Data - 2024-01-01"

@patch("scripts.pipeline.collect._get_ia_credentials")
@patch("boto3.client")
def test_upload_to_ia_client_error(mock_boto_client, mock_creds, tmp_path):
    mock_creds.return_value = ("access", "secret")
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    # Simulate ClientError
    error_response = {'Error': {'Code': '503', 'Message': 'Service Unavailable'}}
    mock_s3.put_object.side_effect = ClientError(error_response, 'PutObject')

    file_path = tmp_path / "test.zip"
    file_path.write_text("dummy content")

    result = upload_to_ia("bucket-id", file_path, "2024-01-01")

    assert result is False

@patch("scripts.pipeline.collect._get_ia_credentials")
def test_upload_to_ia_no_creds(mock_creds, tmp_path):
    mock_creds.return_value = None
    file_path = tmp_path / "test.zip"
    result = upload_to_ia("bucket-id", file_path, "2024-01-01")
    assert result is False

@patch("scripts.pipeline.collect._get_ia_credentials")
@patch("boto3.client")
def test_header_injection(mock_boto_client, mock_creds, tmp_path):
    mock_creds.return_value = ("access", "secret")
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    file_path = tmp_path / "test.zip"
    file_path.write_text("dummy")

    upload_to_ia("bucket-id", file_path, "2024-01-01")

    # Extract the handler
    _, handler = mock_s3.meta.events.register.call_args[0]

    # Test the handler
    params = {'headers': {}}
    handler(params)
    assert params['headers']['x-archive-auto-make-bucket'] == '1'
    assert params['headers']['x-archive-queue-derive'] == '0'
