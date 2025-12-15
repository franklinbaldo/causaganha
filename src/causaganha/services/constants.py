"""Constants for services."""

# Internet Archive configuration
IA_DEFAULT_COLLECTION = "opensource"
IA_DEFAULT_MEDIATYPE = "texts"
IA_DEFAULT_CREATOR = "CausaGanha"
IA_DEFAULT_SUBJECTS = ["judicial", "brazil"]

# Upload retry configuration
DEFAULT_UPLOAD_RETRIES = 3
DEFAULT_RETRY_SLEEP_SECONDS = 5
DEFAULT_UPLOAD_TIMEOUT_SECONDS = 300

# File size limits (in bytes)
MAX_REASONABLE_FILE_SIZE = 1024 * 1024 * 500  # 500MB
