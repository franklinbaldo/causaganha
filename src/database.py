# causaganha/core/database.py
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
import json  # Ensure json is imported
import logging
from datetime import datetime  # Ensure datetime is imported for now()
import uuid  # For generating IDs

# MigrationRunner will be imported in a dedicated migration function
# from migration_runner import MigrationRunner

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections for DuckDB.

    This class is responsible for establishing, providing, and closing database connections.
    It ensures that parent directories for the database file are created if they don't exist.
    Migrations are not run automatically on connect; they should be handled by an
    explicit call to `run_db_migrations`.

    Attributes:
        db_path (Path): The path to the DuckDB database file.
        read_only (bool): If True, connections are opened in read-only mode.
        is_testing_mode (bool): A flag that can be used by other parts of the system
                                to alter behavior during testing (not used by DatabaseManager itself).
    """

    def __init__(self, db_path: Path, read_only: bool = False):
        """
        Initializes the DatabaseManager.

        Args:
            db_path: The path to the DuckDB database file.
            read_only: If True, connections will be read-only. Defaults to False.
        """
        self.db_path = db_path
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self.read_only = read_only
        self.is_testing_mode = False

        if not self.db_path.parent.exists():
            logger.info(
                f"Database directory {self.db_path.parent} does not exist. Creating it."
            )
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        Establishes and returns a database connection.

        If a connection object already exists, it's returned. Otherwise, a new
        connection is established.

        Returns:
            A DuckDBPyConnection object.

        Raises:
            RuntimeError: If the database connection fails.
        """
        if self._connection:
            logger.debug("Returning existing database connection object.")
            return self._connection

        try:
            logger.debug(
                f"Attempting to connect to database: {self.db_path}{' (read-only)' if self.read_only else ''}"
            )
            self._connection = duckdb.connect(
                database=str(self.db_path), read_only=self.read_only
            )
            logger.info(f"Successfully connected to database: {self.db_path}")
            return self._connection
        except Exception as e:
            logger.error(f"Failed to connect to database {self.db_path}: {e}")
            raise RuntimeError(f"Database connection failed for {self.db_path}") from e

    def close(self):
        """Closes the database connection if it is open and sets internal reference to None."""
        if self._connection:
            try:
                self._connection.close()
                logger.info(f"Database connection closed for {self.db_path}")
            except Exception as e:
                logger.warning(
                    f"Error encountered while closing connection for {self.db_path}: {e}",
                    exc_info=True,
                )
            finally:
                self._connection = None
        else:
            logger.debug("No active database connection object to close.")

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Returns an active database connection. Connects if no active connection exists.

        Returns:
            A DuckDBPyConnection object.

        Raises:
            RuntimeError: If a connection cannot be established or is None after attempting.
        """
        if self._connection is None:
            self.connect()

        if self._connection is None:
            logger.error(
                "Database connection is None after connect() call sequence in get_connection."
            )
            raise RuntimeError("Failed to establish a database connection.")
        return self._connection

    def ensure_connection(self):
        """Ensures an active connection is available, connecting if necessary. Alias for get_connection."""
        return self.get_connection()

    def health_check(self) -> bool:
        """
        Performs a simple query (SELECT 1) to check database health.
        Attempts to establish a connection if one is not active.

        Returns:
            True if the health check query executes successfully, False otherwise.
        """
        try:
            conn = self.get_connection()
            conn.execute("SELECT 1").fetchall()
            logger.info(f"Database health check successful for {self.db_path}.")
            return True
        except Exception as e:
            logger.error(f"Database health check failed for {self.db_path}: {e}")
            return False

    def __enter__(self):
        """Context manager entry: connects to the database."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: closes the database connection."""
        self.close()

    def set_testing_mode(self, is_testing: bool):
        """
        Sets a flag for testing mode.
        Note: This flag is for use by other parts of the system and does not alter
        DatabaseManager's own connection behavior beyond logging a warning if changed
        while connected.
        """
        self.is_testing_mode = is_testing
        if self._connection:
            logger.warning(
                "Testing mode changed while a connection object exists. Reconnection may be needed for changes to take full effect if connection parameters depend on this mode."
            )


def run_db_migrations(db_path: Path, migrations_path_override: Optional[Path] = None):
    """
    Runs database migrations using MigrationRunner.

    Args:
        db_path: Path to the DuckDB database file.
        migrations_path_override: Optional path to override the default 'migrations'
                                  directory (located at the project root).
    """
    from migration_runner import MigrationRunner

    logger.info(f"Starting database migrations for: {db_path}")
    try:
        if migrations_path_override:
            migrations_dir = migrations_path_override
            logger.info(f"Using overridden migrations directory: {migrations_dir}")
        else:
            project_root = Path(__file__).resolve().parent.parent
            migrations_dir = project_root / "migrations"
            logger.info(f"Using default migrations directory: {migrations_dir}")

        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

        if not db_path.parent.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory for database: {db_path.parent}")

        with MigrationRunner(db_path, migrations_dir) as runner:
            success = runner.migrate()
            if not success:
                logger.error(f"Database migrations failed for {db_path}.")
                raise RuntimeError(f"Database migrations failed for {db_path}")
        logger.info(f"Database migrations executed successfully for {db_path}.")
    except (OSError, RuntimeError, duckdb.Error, FileNotFoundError) as e:
        logger.error(f"Error during database migrations for {db_path}: {e}")
        raise


class CausaGanhaDB:
    """
    Provides an API for interacting with the CausaGanha application database.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        return self.db_manager.get_connection()

    def get_ratings(self) -> pd.DataFrame:
        return self.conn.execute("""
            SELECT advogado_id, mu, sigma, total_partidas,
                   mu - 3 * sigma as conservative_skill
            FROM ratings
            ORDER BY mu DESC
        """).df()

    def update_rating(
        self, advogado_id: str, mu: float, sigma: float, increment_partidas: bool = True
    ):
        existing_rating = self.get_rating(advogado_id)
        if existing_rating is not None:
            if increment_partidas:
                sql = "UPDATE ratings SET mu = ?, sigma = ?, total_partidas = total_partidas + 1, updated_at = CURRENT_TIMESTAMP WHERE advogado_id = ?"
                self.conn.execute(sql, [mu, sigma, advogado_id])
            else:
                sql = "UPDATE ratings SET mu = ?, sigma = ?, updated_at = CURRENT_TIMESTAMP WHERE advogado_id = ?"
                self.conn.execute(sql, [mu, sigma, advogado_id])
        else:
            total_partidas = 1 if increment_partidas else 0
            # Assuming created_at and updated_at have DEFAULT CURRENT_TIMESTAMP in schema for new inserts
            sql = "INSERT INTO ratings (advogado_id, mu, sigma, total_partidas) VALUES (?, ?, ?, ?)"
            self.conn.execute(sql, [advogado_id, mu, sigma, total_partidas])

    def get_rating(self, advogado_id: str) -> Optional[Dict[str, Any]]:
        result = self.conn.execute(
            "SELECT advogado_id, mu, sigma, total_partidas FROM ratings WHERE advogado_id = ?",
            [advogado_id],
        ).fetchone()
        if result:
            return {
                "advogado_id": result[0],
                "mu": result[1],
                "sigma": result[2],
                "total_partidas": result[3],
            }
        return None

    def add_partida(
        self,
        data_partida: str,
        numero_processo: str,
        equipe_a_ids: List[str],
        equipe_b_ids: List[str],
        ratings_antes_a: Dict[str, Any],
        ratings_antes_b: Dict[str, Any],
        resultado: str,
        ratings_depois_a: Dict[str, Any],
        ratings_depois_b: Dict[str, Any],
    ) -> int:
        max_id_result = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM partidas"
        ).fetchone()
        next_id: int = 1
        if max_id_result and max_id_result[0] is not None:
            next_id = int(max_id_result[0])
        sql = """INSERT INTO partidas (id, data_partida, numero_processo, equipe_a_ids, equipe_b_ids, ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida, ratings_equipe_a_depois, ratings_equipe_b_depois) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.conn.execute(
            sql,
            [
                next_id,
                data_partida,
                numero_processo,
                json.dumps(equipe_a_ids),
                json.dumps(equipe_b_ids),
                json.dumps(ratings_antes_a),
                json.dumps(ratings_antes_b),
                resultado,
                json.dumps(ratings_depois_a),
                json.dumps(ratings_depois_b),
            ],
        )
        return next_id

    def get_partidas(self, limit: Optional[int] = None) -> pd.DataFrame:
        sql = "SELECT * FROM partidas ORDER BY data_partida DESC"
        if limit is not None:
            sql += f" LIMIT {limit}"
        return self.conn.execute(sql).df()

    def get_ranking(self, limit: int = 20) -> pd.DataFrame:
        try:
            return self.conn.execute(f"SELECT * FROM ranking_atual LIMIT {limit}").df()
        except duckdb.CatalogException as e:
            logger.error(f"View 'ranking_atual' not found: {e}")
            return pd.DataFrame()

    def get_statistics(self) -> Optional[Dict[str, Any]]:
        try:
            result = self.conn.execute("SELECT * FROM estatisticas_gerais").fetchone()
            if not result:
                logger.warning("'estatisticas_gerais' view empty.")
                return None
            columns = [desc[0] for desc in self.conn.description or []]
            return dict(zip(columns, result))
        except duckdb.Error as e:
            logger.error(f"Error fetching from 'estatisticas_gerais': {e}")
            return None

    def export_to_csv(self, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        tables = [
            "ratings",
            "partidas",
            "pdf_metadata",
            "decisoes",
            "json_files",
            "job_queue",
        ]
        for table in tables:
            try:
                df = self.conn.execute(f"SELECT * FROM {table}").df()
                df.to_csv(output_dir / f"{table}.csv", index=False, encoding="utf-8")
                logger.info(f"Table {table} exported: {len(df)} records")
            except duckdb.Error as e:
                logger.error(f"Could not export {table}: {e}")
        logger.info(f"CSV backup saved to: {output_dir}")

    def export_database_snapshot(self, output_path: Path) -> bool:
        try:
            logger.info(f"Exporting database snapshot to directory: {output_path}")
            if output_path.exists() and not output_path.is_dir():
                logger.error(f"Output path {output_path} is not a directory.")
                return False
            output_path.mkdir(parents=True, exist_ok=True)
            self.conn.execute(f"EXPORT DATABASE '{output_path}' (FORMAT DUCKDB)")
            if output_path.is_dir() and list(output_path.glob("*.duckdb")):
                logger.info(f"Snapshot exported to: {output_path}")
                return True
            else:
                logger.error(f"Export to {output_path} failed or dir empty.")
                return False
        except (duckdb.Error, OSError) as e:
            logger.error(f"Snapshot export failed for {output_path}: {e}")
            return False

    def get_archive_statistics(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = self.get_statistics() or {}
        # ... (implementation as before) ...
        return stats

    def vacuum(self):
        try:
            self.conn.execute("VACUUM")
            logger.info("Database vacuumed.")
        except duckdb.Error as e:
            logger.error(f"Vacuum failed: {e}")

    def get_db_info(self) -> Dict[str, Any]:
        db_p = self.db_manager.db_path
        size_b = 0
        if db_p.exists():
            if db_p.is_file():
                size_b = db_p.stat().st_size
            elif db_p.is_dir():
                size_b = sum(f.stat().st_size for f in db_p.rglob("*") if f.is_file())
        return {
            "db_path": str(db_p),
            "size_bytes": size_b,
            "size_mb": round(size_b / (1024 * 1024), 2),
            "tables": self._get_table_info(),
        }

    def _get_table_info(self) -> Dict[str, Any]:
        tbl_info: Dict[str, Any] = {}
        for tbl_n in [
            "ratings",
            "partidas",
            "pdf_metadata",
            "decisoes",
            "json_files",
            "job_queue",
        ]:
            try:
                res = self.conn.execute(f"SELECT COUNT(*) FROM {tbl_n}").fetchone()
                tbl_info[tbl_n] = res[0] if res and res[0] is not None else 0
            except duckdb.Error as e:
                tbl_info[tbl_n] = f"Error: {e}"
        return tbl_info

    def queue_diario(self, diario_obj: Any) -> bool:
        try:
            from models.diario import Diario

            if not isinstance(diario_obj, Diario):
                logger.error(f"Expected Diario object, got {type(diario_obj)}")
                return False

            queue_item = diario_obj.queue_item
            required = ["url", "date", "tribunal", "status"]
            if any(
                field not in queue_item or queue_item[field] is None
                for field in required
            ):
                logger.error(f"Missing critical field for {diario_obj.display_name}")
                return False

            meta_str = json.dumps(queue_item.get("metadata", {}))
            date_val = queue_item.get("date")
            date_str = (
                date_val.isoformat()
                if hasattr(date_val, "isoformat")
                else str(date_val)
            )

            item_id = queue_item.get("id", uuid.uuid4().hex)
            current_time = datetime.now()

            self.conn.execute(
                """
                INSERT INTO job_queue (
                    id, url, date, tribunal, filename, metadata, status,
                    ia_identifier, arquivo_path, error_message, retry_count,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (url) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = now(),
                    date = EXCLUDED.date, tribunal = EXCLUDED.tribunal, filename = EXCLUDED.filename,
                    metadata = EXCLUDED.metadata, ia_identifier = EXCLUDED.ia_identifier,
                    arquivo_path = EXCLUDED.arquivo_path,
                    error_message = EXCLUDED.error_message,
                    retry_count = EXCLUDED.retry_count
            """,
                [
                    item_id,
                    queue_item.get("url"),
                    date_str,
                    queue_item.get("tribunal"),
                    queue_item.get("filename"),
                    meta_str,
                    queue_item.get("status", "pending"),
                    queue_item.get("ia_identifier"),
                    queue_item.get("arquivo_path"),
                    queue_item.get("error_message"),
                    queue_item.get("retry_count", 0),
                    current_time,
                    current_time,
                ],
            )
            logger.info(f"Queued/Updated diario: {diario_obj.display_name}")
            return True
        except Exception as e:
            diario_name = (
                diario_obj.display_name
                if hasattr(diario_obj, "display_name")
                else "unknown diario"
            )
            logger.error(f"Error queuing diario {diario_name}: {e}", exc_info=True)
            if isinstance(e, duckdb.Error):
                self.db_manager.close()
            return False

    def get_diarios_by_status(self, status: str) -> List[Any]:
        try:
            from models.diario import Diario

            rows = self.conn.execute(
                """
                SELECT id, url, date, tribunal, filename, metadata, status,
                       ia_identifier, arquivo_path, created_at, updated_at,
                       error_message, retry_count
                FROM job_queue WHERE status = ? ORDER BY created_at ASC""",
                [status],
            ).fetchall()
            diarios_list: List[Any] = []
            for row_data in rows:
                meta_dict = json.loads(row_data[5]) if row_data[5] else {}
                # Pass all fields to from_queue_item, assuming it can handle them
                q_data = {
                    "id": row_data[0],
                    "url": row_data[1],
                    "date": row_data[2],
                    "tribunal": row_data[3],
                    "filename": row_data[4],
                    "metadata": meta_dict,
                    "status": row_data[6],
                    "ia_identifier": row_data[7],
                    "arquivo_path": row_data[8],
                    # 'created_at': row_data[9], 'updated_at': row_data[10], # Not typically in queue_item
                    "error_message": row_data[11],
                    "retry_count": row_data[12],
                }
                try:
                    diarios_list.append(Diario.from_queue_item(q_data))
                except Exception as e_diario:
                    logger.error(
                        f"Failed to create Diario from data for URL {row_data[1]}: {e_diario}",
                        exc_info=True,
                    )
            logger.info(f"Retrieved {len(diarios_list)} diarios with status '{status}'")
            return diarios_list
        except Exception as e:
            logger.error(
                f"Error retrieving diarios by status '{status}': {e}", exc_info=True
            )
            return []

    def update_diario_status(
        self, diario_identifier: Any, new_status: str, **kwargs: Any
    ) -> bool:
        try:
            url_to_update: Optional[str] = None
            if hasattr(diario_identifier, "url") and diario_identifier.url:
                url_to_update = diario_identifier.url
            elif isinstance(diario_identifier, str) and diario_identifier:
                url_to_update = diario_identifier
            else:
                logger.error(
                    f"Invalid diario_identifier for status update: {diario_identifier}"
                )
                return False

            updates: List[str] = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params: List[Any] = [new_status]

            mappings = {
                "ia_identifier": "ia_identifier",
                "arquivo_path": "arquivo_path",
                "pdf_path": "arquivo_path",
                "error_message": "error_message",
                "metadata": "metadata",
                "retry_count": "retry_count",
            }
            for key, val in kwargs.items():
                if key in mappings:
                    updates.append(f"{mappings[key]} = ?")
                    params.append(
                        json.dumps(val)
                        if key == "metadata"
                        else str(val)
                        if val is not None
                        else None
                    )

            query = f"UPDATE job_queue SET {', '.join(updates)} WHERE url = ?"
            params.append(url_to_update)

            result = self.conn.execute(query, params)
            if result.rowcount is not None and result.rowcount > 0:
                logger.info(
                    f"Updated diario {url_to_update} to status {new_status} with {kwargs}"
                )
                return True
            else:
                logger.warning(
                    f"No diario found for URL {url_to_update} to update (rowcount: {result.rowcount})."
                )
                return False
        except Exception as e:
            logger.error(
                f"Error updating diario status for {diario_identifier}: {e}",
                exc_info=True,
            )
            return False

    def get_diarios_by_tribunal(self, tribunal_code: str) -> List[Any]:
        try:
            from models.diario import Diario

            rows = self.conn.execute(
                "SELECT * FROM job_queue WHERE tribunal = ? ORDER BY date DESC, created_at DESC",
                [tribunal_code],
            ).fetchall()
            diarios_list: List[Any] = []
            for row_data in rows:
                meta_dict = json.loads(row_data[5]) if row_data[5] else {}
                q_data = {
                    "id": row_data[0],
                    "url": row_data[1],
                    "date": row_data[2],
                    "tribunal": row_data[3],
                    "filename": row_data[4],
                    "metadata": meta_dict,
                    "status": row_data[6],
                    "ia_identifier": row_data[7],
                    "arquivo_path": row_data[8],
                    "error_message": row_data[11],
                    "retry_count": row_data[12],
                }
                try:
                    diarios_list.append(Diario.from_queue_item(q_data))
                except Exception as e_diario:
                    logger.error(
                        f"Failed to create Diario from data for URL {row_data[1]} (tribunal {tribunal_code}): {e_diario}",
                        exc_info=True,
                    )
            logger.info(
                f"Retrieved {len(diarios_list)} diarios for tribunal '{tribunal_code}'"
            )
            return diarios_list
        except Exception as e:
            logger.error(
                f"Error retrieving diarios for tribunal '{tribunal_code}': {e}",
                exc_info=True,
            )
            return []

    def get_diario_statistics(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "total_diarios": 0,
            "by_status": {},
            "by_tribunal": {},
            "recent_activity_7_days": 0,
        }
        try:
            res = self.conn.execute("SELECT COUNT(*) FROM job_queue").fetchone()
            if res and res[0] is not None:
                stats["total_diarios"] = int(res[0])
            res_status = self.conn.execute(
                "SELECT status, COUNT(*) FROM job_queue GROUP BY status"
            ).fetchall()
            stats["by_status"] = {str(s): int(c) for s, c in res_status}
            res_trib = self.conn.execute(
                "SELECT tribunal, COUNT(*) FROM job_queue GROUP BY tribunal"
            ).fetchall()
            stats["by_tribunal"] = {str(t): int(c) for t, c in res_trib}
            res_recent = self.conn.execute(
                "SELECT COUNT(*) FROM job_queue WHERE created_at >= (CURRENT_DATE - INTERVAL '7 days')"
            ).fetchone()
            if res_recent and res_recent[0] is not None:
                stats["recent_activity_7_days"] = int(res_recent[0])
        except Exception as e:
            logger.error(f"Error getting diario stats: {e}", exc_info=True)
            stats["error"] = str(e)
        return stats
