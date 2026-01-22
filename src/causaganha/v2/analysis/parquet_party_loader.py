"""Load party data from DJEN parquet files.

This module handles loading and joining the normalized parquet files
from Internet Archive DJEN exports to extract structured party information.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import structlog


logger = structlog.get_logger()


@dataclass
class PartyInfo:
    """Structured party information from parquet files."""

    autor: str | None = None
    reu: str | None = None
    outros: list[tuple[str, str]] = field(default_factory=list)  # [(papel, nome), ...]

    def is_inss_reu(self) -> bool:
        """Check if INSS is defendant."""
        return self.reu is not None and "inss" in self.reu.lower()

    def is_inss_autor(self) -> bool:
        """Check if INSS is plaintiff."""
        return self.autor is not None and "inss" in self.autor.lower()

    def has_parties(self) -> bool:
        """Check if any party information is available."""
        return self.autor is not None or self.reu is not None or len(self.outros) > 0


class ParquetPartyLoader:
    """Load and join party data from DJEN parquet files."""

    def __init__(self, parquet_dir: Path | str):
        """Initialize loader with parquet directory.

        Args:
            parquet_dir: Directory containing DJEN parquet files
                        (comunicacoes.parquet, partes.parquet, comunicacao_partes.parquet)
        """
        self.parquet_dir = Path(parquet_dir)

        # Load tables
        logger.info("loading_parquet_tables", dir=str(self.parquet_dir))

        self.comunicacoes = self._load_parquet("comunicacoes.parquet")
        self.partes = self._load_parquet("partes.parquet")
        self.comunicacao_partes = self._load_parquet("comunicacao_partes.parquet")

        logger.info(
            "parquet_tables_loaded",
            comunicacoes=len(self.comunicacoes),
            partes=len(self.partes),
            comunicacao_partes=len(self.comunicacao_partes),
        )

    def _load_parquet(self, filename: str) -> pd.DataFrame:
        """Load a parquet file."""
        file_path = self.parquet_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        return pq.read_table(file_path).to_pandas()

    def get_parties(self, comunicacao_id: str | int) -> PartyInfo:
        """Get parties for a specific comunicacao.

        Args:
            comunicacao_id: Communication ID (can be string or int)

        Returns:
            PartyInfo with extracted party names and roles
        """
        # Convert to string for consistency
        comunicacao_id = str(comunicacao_id)

        # Join tables to get parties
        result = (
            self.comunicacao_partes[self.comunicacao_partes["comunicacao_id"] == comunicacao_id]
            .merge(self.partes, on="parte_id", how="left")
        )

        # Extract parties by role
        parties = PartyInfo()

        for _, row in result.iterrows():
            papel = row["papel"]
            nome = row["nome"]

            if pd.isna(nome):
                continue  # Skip if nome is NaN

            # Normalize name
            nome = str(nome).strip().upper()

            if papel == "A":  # Ativo (Author/Plaintiff)
                parties.autor = nome
            elif papel == "P":  # Passivo (Defendant)
                parties.reu = nome
            else:  # T (Terceiro), D (Outros), etc.
                parties.outros.append((papel, nome))

        logger.debug(
            "parties_extracted",
            comunicacao_id=comunicacao_id,
            autor=parties.autor,
            reu=parties.reu,
            outros_count=len(parties.outros),
        )

        return parties

    def get_parties_batch(self, comunicacao_ids: list[str | int]) -> dict[str, PartyInfo]:
        """Get parties for multiple comunicacoes (optimized batch operation).

        Args:
            comunicacao_ids: List of communication IDs

        Returns:
            Dictionary mapping comunicacao_id to PartyInfo
        """
        # Convert all IDs to strings
        comunicacao_ids = [str(cid) for cid in comunicacao_ids]

        # Filter for requested IDs
        filtered = self.comunicacao_partes[
            self.comunicacao_partes["comunicacao_id"].isin(comunicacao_ids)
        ]

        # Join with partes
        result = filtered.merge(self.partes, on="parte_id", how="left")

        # Group by comunicacao_id and build PartyInfo for each
        parties_dict = {}

        for comunicacao_id in comunicacao_ids:
            comunicacao_parties = result[result["comunicacao_id"] == comunicacao_id]

            party_info = PartyInfo()

            for _, row in comunicacao_parties.iterrows():
                papel = row["papel"]
                nome = row["nome"]

                if pd.isna(nome):
                    continue

                nome = str(nome).strip().upper()

                if papel == "A":
                    party_info.autor = nome
                elif papel == "P":
                    party_info.reu = nome
                else:
                    party_info.outros.append((papel, nome))

            parties_dict[comunicacao_id] = party_info

        logger.info("batch_parties_extracted", count=len(parties_dict))

        return parties_dict
