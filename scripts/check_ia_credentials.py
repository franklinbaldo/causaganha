#!/usr/bin/env python3
"""Check Internet Archive credentials for validity.

This script tests if IA_ACCESS_KEY and IA_SECRET_KEY secrets are valid
by making a simple request to the IA S3 API. It exits with 0 on success,
or 1 if the keys are invalid (e.g. InvalidAccessKeyId).
"""

import os
import sys
import urllib.request
from urllib.error import HTTPError, URLError


def main() -> int:
    """Run the IA credentials check."""
    access_key = os.environ.get("IA_ACCESS_KEY")
    secret_key = os.environ.get("IA_SECRET_KEY")

    if not access_key or not secret_key:
        sys.stderr.write("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY are required.\n")
        return 1

    # Format credentials for S3 API: "LOW access:secret"
    auth_header = f"LOW {access_key}:{secret_key}"

    req = urllib.request.Request("https://s3.us.archive.org")
    req.get_method = lambda: "PUT"
    req.add_header("Authorization", auth_header)

    try:
        # Check scheme explicitly to satisfy security considerations
        if req.full_url.startswith("https://"):
            urllib.request.urlopen(req)  # noqa: S310
    except HTTPError as e:
        body = e.read().decode("utf-8")
        if "InvalidAccessKeyId" in body:
            sys.stderr.write(f"ERROR: Invalid IA credentials for access key '{access_key}'.\n")
            return 1

        # When sending PUT / we expect a 4xx error (like 400 Bad Request)
        # when authentication succeeds but the request itself is incomplete/invalid.
        # So we treat other 4xx/5xx as success for auth purposes, as long as
        # it is not an explicit auth rejection (InvalidAccessKeyId).
        sys.stdout.write(f"Success: IA credentials are valid (received HTTP {e.code}).\n")
        return 0
    except URLError as e:
        sys.stderr.write(f"ERROR: Failed to connect to Internet Archive: {e}\n")
        return 1
    else:
        sys.stdout.write("Success: IA credentials are valid.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
