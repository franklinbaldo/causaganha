from __future__ import annotations

"""Utility functions for anonymizing metadata before upload or storage."""

from typing import Dict, Optional

from .pii_manager import PiiManager


def anonymize_metadata(
    metadata: Dict[str, str], pii_manager: Optional[PiiManager] = None
) -> Dict[str, str]:
    """Replace PII fields in a metadata dictionary using ``PiiManager``.

    Only ``creator`` and ``title`` fields are anonymized for now. When
    ``pii_manager`` is ``None`` the input dictionary is returned unchanged.
    """
    if pii_manager is None:
        return metadata

    sanitized = metadata.copy()
    for field in ("creator", "title"):
        value = sanitized.get(field)
        if value:
            sanitized[field] = pii_manager.get_or_create_pii_mapping(
                value, f"METADATA_{field.upper()}"
            )
    return sanitized
