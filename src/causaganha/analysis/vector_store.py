"""Vector store manager for LanceDB operations."""

from pathlib import Path
from typing import Any

import structlog


try:
    import lancedb
    from lancedb.table import Table
except ImportError:
    lancedb = None  # type: ignore[assignment]
    Table = Any  # type: ignore[assignment]


logger = structlog.get_logger()

# Default LanceDB path
DEFAULT_VECTOR_STORE_PATH = "data/lancedb"


class VectorStore:
    """Manager for LanceDB vector store operations."""

    def __init__(self, db_path: str | Path = DEFAULT_VECTOR_STORE_PATH) -> None:
        """Initialize vector store connection.

        Args:
            db_path: Path to LanceDB database directory.
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db: Any | None = None

        logger.info("vector_store_initialized", db_path=str(self.db_path))

    def connect(self) -> Any:  # noqa: ANN401
        """Connect to LanceDB database.

        Returns:
            Database connection.
        """
        if self.db is None:
            if lancedb is None:
                msg = (
                    "lancedb is not installed. Please install with "
                    "`uv pip install lancedb` or `uv pip install causaganha[embeddings]`"
                )
                raise ImportError(msg)
            self.db = lancedb.connect(str(self.db_path))
            logger.info("vector_store_connected", db_path=str(self.db_path))

        return self.db

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            table_name: Name of the table to check.

        Returns:
            True if table exists, False otherwise.
        """
        return table_name in self.list_tables()

    def create_table(
        self,
        table_name: str,
        data: list[dict[str, Any]],
        mode: str = "create",
    ) -> Table:
        """Create a table in the vector store.

        Args:
            table_name: Name for the new table.
            data: List of records to insert. Each record must have:
                - vector: list[float] - The embedding vector
                - Other fields as needed (e.g., intimation_id, outcome, text)
            mode: Creation mode - "create", "overwrite", or "append".

        Returns:
            The created table.

        Raises:
            ValueError: If data is empty or invalid.
        """
        if not data:
            msg = "Cannot create table with empty data"
            raise ValueError(msg)

        db = self.connect()

        # Validate data structure
        if "vector" not in data[0]:
            msg = "Data records must have 'vector' field"
            raise ValueError(msg)

        logger.info(
            "creating_table",
            table_name=table_name,
            num_records=len(data),
            mode=mode,
        )

        table = db.create_table(table_name, data=data, mode=mode)

        logger.info(
            "table_created",
            table_name=table_name,
            num_records=len(data),
        )

        return table

    def get_table(self, table_name: str) -> Table:
        """Get an existing table from the database.

        Args:
            table_name: Name of the table.

        Returns:
            The table object.

        Raises:
            ValueError: If table doesn't exist.
        """
        if not self.table_exists(table_name):
            msg = f"Table '{table_name}' does not exist"
            raise ValueError(msg)

        db = self.connect()
        return db.open_table(table_name)

    def add_documents(
        self,
        table_name: str,
        documents: list[dict[str, Any]],
    ) -> None:
        """Add documents to an existing table.

        Args:
            table_name: Name of the table.
            documents: List of document records to add.

        Raises:
            ValueError: If table doesn't exist.
        """
        table = self.get_table(table_name)

        logger.info(
            "adding_documents",
            table_name=table_name,
            num_documents=len(documents),
        )

        table.add(documents)

        logger.info(
            "documents_added",
            table_name=table_name,
            num_documents=len(documents),
        )

    def search(
        self,
        table_name: str,
        query_vector: list[float],
        k: int = 5,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for k nearest neighbors in the vector store.

        Args:
            table_name: Name of the table to search.
            query_vector: Query embedding vector.
            k: Number of nearest neighbors to return.
            columns: Optional list of columns to return. If None, returns all.

        Returns:
            List of k nearest neighbor records with distance scores.
        """
        table = self.get_table(table_name)

        logger.debug(
            "searching_vectors",
            table_name=table_name,
            k=k,
            vector_dim=len(query_vector),
        )

        # Perform vector search
        results = table.search(query_vector).limit(k)

        if columns:
            results = results.select(columns)

        # Convert to list of dicts
        results_df = results.to_pandas()
        records = results_df.to_dict("records")

        logger.debug(
            "search_complete",
            table_name=table_name,
            results_found=len(records),
        )

        return records

    def delete_table(self, table_name: str) -> None:
        """Delete a table from the database.

        Args:
            table_name: Name of the table to delete.
        """
        if not self.table_exists(table_name):
            logger.warning("table_not_found_for_deletion", table_name=table_name)
            return

        db = self.connect()
        db.drop_table(table_name)

        logger.info("table_deleted", table_name=table_name)

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get information about a table.

        Args:
            table_name: Name of the table.

        Returns:
            Dictionary with table metadata.
        """
        table = self.get_table(table_name)

        # Get record count
        table_df = table.to_pandas()
        num_records = len(table_df)

        # Get schema
        schema = table_df.dtypes.to_dict()

        info = {
            "table_name": table_name,
            "num_records": num_records,
            "schema": {col: str(dtype) for col, dtype in schema.items()},
        }

        logger.debug("table_info_retrieved", **info)

        return info

    def list_tables(self) -> list[str]:
        """List all tables in the database.

        Returns:
            List of table names.
        """
        db = self.connect()
        # Use the new list_tables() API which returns a response object
        response = db.list_tables()
        tables = response.tables if hasattr(response, "tables") else response

        logger.debug("tables_listed", num_tables=len(tables))

        return tables
