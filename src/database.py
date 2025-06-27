# causaganha/core/database.py
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging
import tempfile
import os # Required for os.remove
from migration_runner import MigrationRunner

logger = logging.getLogger(__name__)


class CausaGanhaDB:
    """
    Classe unificada para gerenciar todos os dados do CausaGanha em DuckDB.

    Centraliza:
    - Ratings OpenSkill (advogados)
    - Partidas (histórico de matches)
    - Metadados de PDFs
    - Decisões extraídas
    - Arquivos JSON processados
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        self.conn = None
        self._temp_db_file_obj = None  # To store NamedTemporaryFile object itself
        self._temp_db_file_path = None # To store the path of the temp file

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Conecta ao banco DuckDB e roda migrações."""
        db_to_connect_str = None
        if self.db_path:
            db_to_connect_str = str(self.db_path)
            # If a specific db_path is given, ensure it's not an empty file that confuses DuckDB
            # It's generally expected that if db_path is provided, it's either a valid DB or non-existent
            if self.db_path.exists() and self.db_path.stat().st_size == 0:
                logger.warning(f"Provided db_path {self.db_path} is an empty file. Removing it to allow DuckDB to initialize fresh.")
                self.db_path.unlink()
            logger.info("Conectando ao DuckDB: %s", self.db_path)
        else:
            # Create a temporary file name, then delete it so DuckDB can create it.
            # This ensures DuckDB initializes the file correctly.
            with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as tmp_file_for_name:
                self._temp_db_file_path = Path(tmp_file_for_name.name) # Get name, file is deleted on with-exit

            # self._temp_db_file_obj is not used to keep the file open here,
            # as DuckDB needs to manage the file lifecycle once connected.
            # We only store the path for later cleanup.

            db_to_connect_str = str(self._temp_db_file_path)
            self.db_path = self._temp_db_file_path # Update self.db_path for migrations etc.
            logger.info("Usando banco de dados DuckDB temporário: %s", db_to_connect_str)

        self.conn = duckdb.connect(db_to_connect_str)
        self._run_migrations()


    def close(self):
        """Fecha conexão com banco."""
        if self.conn:
            self.conn.close()
            self.conn = None

        # Clean up temporary file path if it was used
        if self._temp_db_file_path:
            try:
                if self._temp_db_file_path.exists():
                    self._temp_db_file_path.unlink()
                    logger.info("Arquivo de banco de dados temporário removido: %s", self._temp_db_file_path)
            except Exception as e:
                logger.error("Erro ao remover arquivo de banco de dados temporário %s: %s", self._temp_db_file_path, e)
            finally:
                self._temp_db_file_path = None # Clear the path


    def _run_migrations(self):
        """Executa migrações de banco de dados."""
        try:
            # Close current connection temporarily
            if self.conn:
                self.conn.close() # Ensure connection is closed before MigrationRunner tries to use the file

            if not self.db_path:
                raise RuntimeError("db_path not set before running migrations.")

            migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
            # Ensure migrations_dir exists
            if not migrations_dir.is_dir():
                logger.error(f"Directory for migrations not found: {migrations_dir}")
                raise RuntimeError(f"Migrations directory not found: {migrations_dir}")

            with MigrationRunner(self.db_path, migrations_dir) as runner:
                success = runner.migrate()
                if not success:
                    raise RuntimeError("Database migrations failed")

            # Reconnect
            self.conn = duckdb.connect(str(self.db_path))
            logger.info("Migrações DuckDB executadas com sucesso")

        except (OSError, RuntimeError, duckdb.Error) as e:
            logger.error("Erro ao executar migrações: %s", e)
            raise

    # =====================================
    # MÉTODOS: Ratings OpenSkill
    # =====================================

    def get_ratings(self) -> pd.DataFrame:
        """Retorna todos os ratings ordenados por μ."""
        return self.conn.execute("""
            SELECT advogado_id, mu, sigma, total_partidas,
                   mu - 3 * sigma as conservative_skill
            FROM ratings
            ORDER BY mu DESC
        """).df()

    def update_rating(
        self, advogado_id: str, mu: float, sigma: float, increment_partidas: bool = True
    ):
        """Atualiza rating de um advogado."""
        existing = self.get_rating(advogado_id)
        if existing:
            if increment_partidas:
                sql = """
                    UPDATE ratings SET
                        mu = ?, sigma = ?, total_partidas = total_partidas + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE advogado_id = ?"""
                self.conn.execute(sql, [mu, sigma, advogado_id])
            else:
                sql = """
                    UPDATE ratings SET mu = ?, sigma = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE advogado_id = ?"""
                self.conn.execute(sql, [mu, sigma, advogado_id])
        else:
            total_partidas = 1 if increment_partidas else 0
            sql = """
                INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""
            self.conn.execute(sql, [advogado_id, mu, sigma, total_partidas])

    def get_rating(self, advogado_id: str) -> Optional[Dict]:
        result = self.conn.execute(
            "SELECT advogado_id, mu, sigma, total_partidas FROM ratings WHERE advogado_id = ?",
            [advogado_id],
        ).fetchone()
        if result:
            return {"advogado_id": result[0], "mu": result[1], "sigma": result[2], "total_partidas": result[3]}
        return None

    # =====================================
    # MÉTODOS: Partidas
    # =====================================
    def add_partida(self, data_partida: str, numero_processo: str, equipe_a_ids: List[str], equipe_b_ids: List[str],
                    ratings_antes_a: Dict[str, tuple], ratings_antes_b: Dict[str, tuple], resultado: str,
                    ratings_depois_a: Dict[str, tuple], ratings_depois_b: Dict[str, tuple]) -> int:
        max_id_result = self.conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM partidas").fetchone()
        next_id = max_id_result[0]
        sql = """
            INSERT INTO partidas (id, data_partida, numero_processo, equipe_a_ids, equipe_b_ids,
                                  ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
                                  ratings_equipe_a_depois, ratings_equipe_b_depois)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        self.conn.execute(sql, [next_id, data_partida, numero_processo, json.dumps(equipe_a_ids),
                               json.dumps(equipe_b_ids), json.dumps(ratings_antes_a),
                               json.dumps(ratings_antes_b), resultado, json.dumps(ratings_depois_a),
                               json.dumps(ratings_depois_b)])
        return next_id

    def get_partidas(self, limit: int = None) -> pd.DataFrame:
        sql = "SELECT * FROM partidas ORDER BY data_partida DESC"
        if limit:
            sql += f" LIMIT {limit}"
        return self.conn.execute(sql).df()

    # =====================================
    # MÉTODOS: Estatísticas e Views
    # =====================================
    def get_ranking(self, limit: int = 20) -> pd.DataFrame:
        return self.conn.execute(f"SELECT * FROM ranking_atual LIMIT {limit}").df()

    def get_statistics(self) -> Dict:
        result = self.conn.execute("SELECT * FROM estatisticas_gerais").fetchone()
        columns = ["total_advogados", "advogados_ativos", "mu_medio", "sigma_medio", "max_partidas",
                   "total_partidas", "total_pdfs", "pdfs_arquivados", "total_decisoes",
                   "decisoes_validas", "total_json_files", "json_files_processados"]
        return dict(zip(columns, result))

    # =====================================
    # MÉTODOS: Backup e Utilitários
    # =====================================
    def export_to_csv(self, output_dir: Path):
        output_dir.mkdir(exist_ok=True)
        tables = ["ratings", "partidas", "pdf_metadata", "decisoes", "json_files"]
        for table in tables:
            df = self.conn.execute(f"SELECT * FROM {table}").df()
            df.to_csv(output_dir / f"{table}.csv", index=False)
            logger.info("Tabela %s exportada: %d registros", table, len(df))
        logger.info("Backup CSV completo salvo em: %s", output_dir)

    def export_database_snapshot(self, output_path: Path) -> bool:
        try:
            logger.info("Exporting database snapshot to: %s", output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn.execute(f"EXPORT DATABASE '{output_path}' (FORMAT DUCKDB)")
            if output_path.exists() and output_path.stat().st_size > 0:
                size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info("Database snapshot exported successfully: %.2f MB", size_mb)
                return True
            else:
                logger.error("Export failed: output file is missing or empty")
                return False
        except (duckdb.Error, OSError) as e:
            logger.error("Database export failed: %s", e)
            return False

    def get_archive_statistics(self) -> Dict[str, Any]:
        stats = self.get_statistics()
        try:
            date_range = self.conn.execute("""
                SELECT MIN(data_partida) as earliest_match, MAX(data_partida) as latest_match,
                       COUNT(DISTINCT data_partida) as unique_dates
                FROM partidas""").fetchone()
            if date_range and date_range[0]:
                stats["data_range"] = {"earliest_match": date_range[0], "latest_match": date_range[1],
                                       "unique_dates": date_range[2]}
            top_performers = self.conn.execute("""
                SELECT COUNT(*) as active_lawyers_count FROM ratings
                WHERE total_partidas >= 5 AND mu > 25.0""").fetchone()
            if top_performers:
                stats["active_lawyers_5plus"] = top_performers[0]
        except (duckdb.Error, duckdb.CatalogException) as e:
            logger.warning("Could not get additional archive statistics: %s", e)
        return stats

    def vacuum(self):
        self.conn.execute("VACUUM")
        logger.info("Database vacuum concluído")

    def get_db_info(self) -> Dict:
        size_bytes = 0
        db_path_str = "Temporary in-memory DB (no file path)"

        if self.db_path:
            db_path_str = str(self.db_path)
            if self.db_path.exists():
                 try:
                    size_bytes = self.db_path.stat().st_size
                 except FileNotFoundError: # Could have been cleaned up by `close` if temp
                    size_bytes = 0
            else: # Path was provided but does not exist (e.g. before connect or after failed cleanup)
                size_bytes = 0

        size_mb = size_bytes / (1024 * 1024)
        return {"db_path": db_path_str, "size_bytes": size_bytes,
                "size_mb": round(size_mb, 2), "tables": self._get_table_info()}

    def _get_table_info(self) -> Dict:
        tables = {}
        table_names = ["ratings", "partidas", "pdf_metadata", "decisoes", "json_files", "job_queue"] # Added job_queue
        if not self.conn:
            logger.warning("No database connection available to fetch table info.")
            for table in table_names:
                tables[table] = "N/A (no connection)"
            return tables
        for table in table_names:
            try:
                count_result = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                tables[table] = count_result[0] if count_result else 0
            except (duckdb.Error, duckdb.CatalogException) as e:
                tables[table] = f"Error: {e}"
            except Exception as e:
                logger.error(f"Unexpected error fetching info for table {table}: {e}")
                tables[table] = f"Unexpected Error: {e}"
        return tables

    # Diario dataclass support methods
    def queue_diario(self, diario) -> bool:
        try:
            from models.diario import Diario
            if not isinstance(diario, Diario):
                raise ValueError("Expected Diario object")
            queue_item = diario.queue_item
            self.conn.execute("""
                INSERT INTO job_queue (url, date, tribunal, filename, metadata, status, ia_identifier, arquivo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (url) DO UPDATE SET
                    status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP""",
                [queue_item['url'], queue_item['date'], queue_item['tribunal'], queue_item['filename'],
                 json.dumps(queue_item['metadata']), queue_item['status'], queue_item['ia_identifier'],
                 queue_item['arquivo_path']])
            logger.info(f"Queued diario: {diario.display_name}")
            return True
        except Exception as e:
            logger.error(f"Error queuing diario {getattr(diario, 'display_name', 'unknown')}: {e}")
            return False

    def get_diarios_by_status(self, status: str) -> List:
        try:
            from models.diario import Diario
            rows = self.conn.execute("""
                SELECT url, date, tribunal, filename, metadata, status, ia_identifier, arquivo_path
                FROM job_queue WHERE status = ? ORDER BY created_at""", [status]).fetchall()
            diarios = []
            for row in rows:
                queue_data = {'url': row[0], 'date': row[1], 'tribunal': row[2], 'filename': row[3],
                              'metadata': json.loads(row[4]) if row[4] else {}, 'status': row[5],
                              'ia_identifier': row[6], 'arquivo_path': row[7]}
                diarios.append(Diario.from_queue_item(queue_data))
            logger.info(f"Retrieved {len(diarios)} diarios with status '{status}'")
            return diarios
        except Exception as e:
            logger.error(f"Error retrieving diarios with status '{status}': {e}")
            return []

    def update_diario_status(self, diario, new_status: str, **kwargs) -> bool:
        try:
            url = diario.url if hasattr(diario, 'url') else str(diario)
            update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            values = [new_status]
            field_mappings = {'ia_identifier': 'ia_identifier', 'arquivo_path': 'arquivo_path',
                              'pdf_path': 'arquivo_path', 'error_message': 'error_message'}
            for key, value in kwargs.items():
                if key in field_mappings:
                    db_field = field_mappings[key]
                    update_fields.append(f"{db_field} = ?")
                    values.append(str(value) if value else None)
            query = f"UPDATE job_queue SET {', '.join(update_fields)} WHERE url = ?"
            values.append(url)
            result = self.conn.execute(query, values)
            if result.rowcount > 0:
                logger.info(f"Updated diario status: {url} -> {new_status}")
                return True
            else:
                logger.warning(f"No diario found with URL: {url}")
                return False
        except Exception as e:
            logger.error(f"Error updating diario status: {e}")
            return False

    def get_diarios_by_tribunal(self, tribunal: str) -> List:
        try:
            from models.diario import Diario
            rows = self.conn.execute("""
                SELECT url, date, tribunal, filename, metadata, status, ia_identifier, arquivo_path
                FROM job_queue WHERE tribunal = ? ORDER BY date DESC""", [tribunal]).fetchall()
            diarios = []
            for row in rows:
                queue_data = {'url': row[0], 'date': row[1], 'tribunal': row[2], 'filename': row[3],
                              'metadata': json.loads(row[4]) if row[4] else {}, 'status': row[5],
                              'ia_identifier': row[6], 'arquivo_path': row[7]}
                diarios.append(Diario.from_queue_item(queue_data))
            logger.info(f"Retrieved {len(diarios)} diarios for tribunal '{tribunal}'")
            return diarios
        except Exception as e:
            logger.error(f"Error retrieving diarios for tribunal '{tribunal}': {e}")
            return []

    def get_diario_statistics(self) -> Dict[str, Any]:
        try:
            stats = {}
            total_result = self.conn.execute("SELECT COUNT(*) FROM job_queue").fetchone()
            stats['total_diarios'] = total_result[0] if total_result else 0
            status_results = self.conn.execute("""
                SELECT status, COUNT(*) FROM job_queue GROUP BY status ORDER BY COUNT(*) DESC""").fetchall()
            stats['by_status'] = {status: count for status, count in status_results}
            tribunal_results = self.conn.execute("""
                SELECT tribunal, COUNT(*) FROM job_queue GROUP BY tribunal ORDER BY COUNT(*) DESC""").fetchall()
            stats['by_tribunal'] = {tribunal: count for tribunal, count in tribunal_results}
            recent_results = self.conn.execute("""
                SELECT COUNT(*) FROM job_queue WHERE created_at >= CURRENT_DATE - INTERVAL 7 DAY""").fetchone()
            stats['recent_activity'] = recent_results[0] if recent_results else 0
            return stats
        except Exception as e:
            logger.error(f"Error getting diario statistics: {e}")
            return {}
