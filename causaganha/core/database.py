# causaganha/core/database.py
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging
from .migration_runner import MigrationRunner

logger = logging.getLogger(__name__)


class CausaGanhaDB:
    """
    Classe unificada para gerenciar todos os dados do CausaGanha em DuckDB.

    Centraliza:
    - Ratings TrueSkill (advogados)
    - Partidas (histórico de matches)
    - Metadados de PDFs
    - Decisões extraídas
    - Arquivos JSON processados
    """

    def __init__(self, db_path: Path = Path("data/causaganha.duckdb")):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Conecta ao banco DuckDB e roda migrações."""
        self.conn = duckdb.connect(str(self.db_path))
        self._run_migrations()
        logger.info("Conectado ao DuckDB: %s", self.db_path)

    def close(self):
        """Fecha conexão com banco."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _run_migrations(self):
        """Executa migrações de banco de dados."""
        try:
            # Close current connection temporarily
            if self.conn:
                self.conn.close()

            # Run migrations using MigrationRunner
            migrations_dir = Path(__file__).parent.parent.parent / "migrations"
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
    # MÉTODOS: Ratings TrueSkill
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
        # Verificar se advogado já existe
        existing = self.get_rating(advogado_id)

        if existing:
            # Atualizar registro existente
            if increment_partidas:
                sql = """
                    UPDATE ratings SET 
                        mu = ?, 
                        sigma = ?, 
                        total_partidas = total_partidas + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE advogado_id = ?
                """
                self.conn.execute(sql, [mu, sigma, advogado_id])
            else:
                sql = """
                    UPDATE ratings SET 
                        mu = ?, 
                        sigma = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE advogado_id = ?
                """
                self.conn.execute(sql, [mu, sigma, advogado_id])
        else:
            # Inserir novo registro
            total_partidas = 1 if increment_partidas else 0
            sql = """
                INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            self.conn.execute(sql, [advogado_id, mu, sigma, total_partidas])

    def get_rating(self, advogado_id: str) -> Optional[Dict]:
        """Retorna rating específico de um advogado."""
        result = self.conn.execute(
            """
            SELECT advogado_id, mu, sigma, total_partidas
            FROM ratings WHERE advogado_id = ?
        """,
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

    # =====================================
    # MÉTODOS: Partidas
    # =====================================

    def add_partida(
        self,
        data_partida: str,
        numero_processo: str,
        equipe_a_ids: List[str],
        equipe_b_ids: List[str],
        ratings_antes_a: Dict[str, tuple],
        ratings_antes_b: Dict[str, tuple],
        resultado: str,
        ratings_depois_a: Dict[str, tuple],
        ratings_depois_b: Dict[str, tuple],
    ) -> int:
        """Adiciona nova partida e retorna ID."""
        # Obter próximo ID
        max_id_result = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM partidas"
        ).fetchone()
        next_id = max_id_result[0]

        sql = """
            INSERT INTO partidas (
                id, data_partida, numero_processo, equipe_a_ids, equipe_b_ids,
                ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
                ratings_equipe_a_depois, ratings_equipe_b_depois
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

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

    def get_partidas(self, limit: int = None) -> pd.DataFrame:
        """Retorna histórico de partidas."""
        sql = "SELECT * FROM partidas ORDER BY data_partida DESC"
        if limit:
            sql += f" LIMIT {limit}"
        return self.conn.execute(sql).df()

    # =====================================
    # MÉTODOS: Estatísticas e Views
    # =====================================

    def get_ranking(self, limit: int = 20) -> pd.DataFrame:
        """Retorna ranking atual."""
        return self.conn.execute(f"""
            SELECT * FROM ranking_atual LIMIT {limit}
        """).df()

    def get_statistics(self) -> Dict:
        """Retorna estatísticas gerais do sistema."""
        result = self.conn.execute("SELECT * FROM estatisticas_gerais").fetchone()

        columns = [
            "total_advogados",
            "advogados_ativos",
            "mu_medio",
            "sigma_medio",
            "max_partidas",
            "total_partidas",
            "total_pdfs",
            "pdfs_arquivados",
            "total_decisoes",
            "decisoes_validas",
            "total_json_files",
            "json_files_processados",
        ]

        return dict(zip(columns, result))

    # =====================================
    # MÉTODOS: Backup e Utilitários
    # =====================================

    def export_to_csv(self, output_dir: Path):
        """Exporta todas as tabelas para CSV (backup)."""
        output_dir.mkdir(exist_ok=True)

        tables = ["ratings", "partidas", "pdf_metadata", "decisoes", "json_files"]
        for table in tables:
            df = self.conn.execute(f"SELECT * FROM {table}").df()
            df.to_csv(output_dir / f"{table}.csv", index=False)
            logger.info("Tabela %s exportada: %d registros", table, len(df))

        logger.info("Backup CSV completo salvo em: %s", output_dir)

    def export_database_snapshot(self, output_path: Path) -> bool:
        """
        Export complete database snapshot using DuckDB EXPORT.
        
        Args:
            output_path: Path where the database snapshot will be saved
            
        Returns:
            True if export was successful
        """
        try:
            logger.info("Exporting database snapshot to: %s", output_path)
            
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use DuckDB EXPORT command for consistent snapshot
            self.conn.execute(f"EXPORT DATABASE '{output_path}' (FORMAT DUCKDB)")
            
            # Verify the exported file exists and has content
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
        """Get comprehensive statistics for archive metadata."""
        stats = self.get_statistics()
        
        # Add additional archive-specific statistics
        try:
            # Get date range of data
            date_range = self.conn.execute("""
                SELECT 
                    MIN(data_partida) as earliest_match,
                    MAX(data_partida) as latest_match,
                    COUNT(DISTINCT data_partida) as unique_dates
                FROM partidas
            """).fetchone()
            
            if date_range and date_range[0]:
                stats["data_range"] = {
                    "earliest_match": date_range[0],
                    "latest_match": date_range[1], 
                    "unique_dates": date_range[2]
                }
            
            # Get top performers for metadata
            top_performers = self.conn.execute("""
                SELECT COUNT(*) as active_lawyers_count
                FROM ratings 
                WHERE total_partidas >= 5 AND mu > 25.0
            """).fetchone()
            
            if top_performers:
                stats["active_lawyers_5plus"] = top_performers[0]
                
        except (duckdb.Error, duckdb.CatalogException) as e:
            logger.warning("Could not get additional archive statistics: %s", e)
        
        return stats

    def vacuum(self):
        """Otimiza banco de dados."""
        self.conn.execute("VACUUM")
        logger.info("Database vacuum concluído")

    def get_db_info(self) -> Dict:
        """Retorna informações sobre o banco."""
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        size_mb = size_bytes / (1024 * 1024)

        return {
            "db_path": str(self.db_path),
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2),
            "tables": self._get_table_info(),
        }

    def _get_table_info(self) -> Dict:
        """Retorna informação sobre tabelas."""
        tables = {}
        table_names = ["ratings", "partidas", "pdf_metadata", "decisoes", "json_files"]

        for table in table_names:
            try:
                count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                tables[table] = count
            except (duckdb.Error, duckdb.CatalogException) as e:
                tables[table] = f"Error: {e}"

        return tables
