import json
import logging
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def upload_file_to_gdrive(file_path: Path) -> None:
    """Upload a file to Google Drive using service account credentials.

    Requires the environment variable ``GDRIVE_SERVICE_ACCOUNT_JSON`` containing
    the service account credentials JSON. Optionally ``GDRIVE_FOLDER_ID`` can
    specify the destination folder.
    """
    creds_json = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        logging.info(
            "GDRIVE_SERVICE_ACCOUNT_JSON not set; skipping Google Drive upload"
        )
        return

    folder_id = os.getenv("GDRIVE_FOLDER_ID")

    try:
        creds_data = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        service = build("drive", "v3", credentials=creds)
        file_metadata = {"name": file_path.name}
        if folder_id:
            file_metadata["parents"] = [folder_id]
        media = MediaFileUpload(str(file_path), mimetype="application/pdf")
        service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        logging.info("Uploaded %s to Google Drive", file_path.name)
    except (OSError, IOError, ValueError, RuntimeError) as e:
        logging.error("Error uploading %s to Google Drive: %s", file_path.name, e)
