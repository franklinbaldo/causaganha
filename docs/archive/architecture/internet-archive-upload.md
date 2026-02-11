# Internet Archive Upload Implementation

## Overview

The `causaganha` project uploads collected data and assets to the [Internet Archive (IA)](https://archive.org). While IA provides an S3-compatible API, we use **httpx** for uploads instead of the standard AWS SDK (**boto3**).

## Why httpx? (and Why Not boto3)

The codebase has historically attempted to use `boto3`, but it consistently failed with **HTTP 411 (Length Required)** errors and metadata issues.

### The boto3 Incompatibility

1.  **Header Prefixing**: `boto3` is hardcoded to use AWS-standard metadata headers (`x-amz-meta-*`). Internet Archive's S3 API requires metadata headers to start with `x-archive-meta-*`.
2.  **Content-Length Handling**: `boto3` (and the underlying `botocore`) sometimes fails to set the `Content-Length` header in a way that the IA S3 frontend expects when performing certain PUT operations, leading to HTTP 411 errors.
3.  **Integrity Checks**: IA requires `Content-MD5` for integrity, which is easier to control and pass explicitly through a direct HTTP client.

### History (PR #348)

The project initially used `httpx`, then attempted to migrate to `boto3` for "standardization." This resulted in broken uploads (HTTP 411). **PR #348** reverted the change back to `httpx`. A subsequent attempt to use `boto3` failed again, confirming that direct HTTP PUT requests are the most reliable method for IA interaction.

## Implementation Details

The current implementation is located in `scripts/pipeline/collect.py` (specifically the `upload_to_ia()` function).

### Key Requirements

*   **Endpoint**: `s3.us.archive.org`
*   **Method**: `PUT`
*   **Headers**:
    *   `Authorization`: `LOW <access_key>:<secret_key>`
    *   `x-archive-meta-collection`: The target IA collection (e.g., `causaganha`).
    *   `x-archive-meta-mediatype`: Typically `data` or `texts`.
    *   `x-archive-meta-*`: Any custom metadata (must use this prefix).
    *   `Content-MD5`: Base64 encoded MD5 hash of the body.

### Retry Strategy

The upload logic implements an exponential backoff retry strategy using a shared `httpx.Client` for connection pooling. This handles transient network issues or temporary IA service instability.

## References

*   [Internet Archive S3 API Documentation](https://archive.org/services/docs/api/ias3.html)
*   PR #348: "Revert boto3 → back to httpx (HTTP 411 fix)"
*   Commit `f4707c4`: Final stabilization of httpx implementation.
