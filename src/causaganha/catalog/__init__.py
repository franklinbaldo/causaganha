"""DuckDB metadata catalog module for CausaGanha.

This module provides functionality to create lightweight DuckDB catalog files
that contain only view definitions referencing remote Parquet files on Internet Archive.
"""

from causaganha.catalog.creator import CatalogCreator

__all__ = ["CatalogCreator"]
