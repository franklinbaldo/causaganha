"""Backwards-compat shim — canonical module moved to causaganha.pipeline.ia_s3.

Re-exports the full public API so that existing ``from scripts.pipeline.ia_s3 import X``
call-sites keep working without modification.
"""

# Re-export pattern: this shim exists only for backwards compatibility.
# Add new symbols here when the canonical module gains public API.
from causaganha.pipeline.ia_s3 import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    CircuitBreaker,
    compute_md5,
    create_upload_client,
    get_ia_item_id,
    get_ia_s3_auth,
    parse_deadline,
    upload_to_ia,
)


__all__ = [
    "HTTP_500_INTERNAL_SERVER_ERROR",
    "CircuitBreaker",
    "compute_md5",
    "create_upload_client",
    "get_ia_item_id",
    "get_ia_s3_auth",
    "parse_deadline",
    "upload_to_ia",
]
