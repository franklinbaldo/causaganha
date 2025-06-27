"""
Diario dataclass for unified tribunal document representation.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class Diario:
    """
    Unified representation of a judicial diary from any tribunal.

    This dataclass provides a common interface for handling judicial documents
    across different tribunals while maintaining compatibility with the existing
    job_queue database schema.
    """

    tribunal: str  # 'tjro', 'tjsp', etc.
    data: date
    url: str
    filename: Optional[str] = None
    hash: Optional[str] = None
    pdf_path: Optional[Path] = None
    ia_identifier: Optional[str] = None
    status: str = "pending"  # pending, downloaded, analyzed, scored
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Human-readable identifier for this diario."""
        return f"{self.tribunal.upper()} - {self.data.isoformat()}"

    @property
    def queue_item(self) -> Dict[str, Any]:
        """Convert to job_queue table format for existing database."""
        return {
            "url": self.url,
            "date": self.data.isoformat(),
            "tribunal": self.tribunal,
            "filename": self.filename,
            "metadata": self.metadata,
            "ia_identifier": self.ia_identifier,
            "status": self.status,
            "arquivo_path": str(self.pdf_path) if self.pdf_path else None,
        }

    @classmethod
    def from_queue_item(cls, queue_row: Dict[str, Any]) -> "Diario":
        """Create Diario from existing job_queue database row."""
        # Handle metadata field - could be JSON string or dict
        metadata = queue_row.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        return cls(
            tribunal=queue_row["tribunal"],
            data=date.fromisoformat(queue_row["date"]),
            url=queue_row["url"],
            filename=queue_row.get("filename"),
            ia_identifier=queue_row.get("ia_identifier"),
            status=queue_row.get("status", "pending"),
            metadata=metadata,
            pdf_path=Path(queue_row["arquivo_path"])
            if queue_row.get("arquivo_path")
            else None,
        )

    def update_status(self, new_status: str, **kwargs) -> None:
        """Update diario status and any additional fields."""
        self.status = new_status
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tribunal": self.tribunal,
            "data": self.data.isoformat(),
            "url": self.url,
            "filename": self.filename,
            "hash": self.hash,
            "pdf_path": str(self.pdf_path) if self.pdf_path else None,
            "ia_identifier": self.ia_identifier,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Diario":
        """Create Diario from dictionary."""
        data_copy = data.copy()
        data_copy["data"] = date.fromisoformat(data_copy["data"])
        if data_copy.get("pdf_path"):
            data_copy["pdf_path"] = Path(data_copy["pdf_path"])
        return cls(**data_copy)
