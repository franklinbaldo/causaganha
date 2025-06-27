# causaganha/core/database.py
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging
# MigrationRunner is no longer imported or used directly here.
# from migration_runner import MigrationRunner

logger = logging.getLogger(__name__)


class CausaGanhaDB:
    """
    Classe unificada para gerenciar todos os dados do CausaGanha em DuckDB.
    Schema is now created directly in connect() if tables don't exist.
    """

    SCHEMA_STATEMENTS = [
        # From 001_init.sql
        """CREATE TABLE IF NOT EXISTS ratings (
            advogado_id VARCHAR PRIMARY KEY,
            mu DOUBLE NOT NULL DEFAULT 25.0,
            sigma DOUBLE NOT NULL DEFAULT 8.333,
            total_partidas INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS partidas (
            id INTEGER,
            data_partida DATE NOT NULL,
            numero_processo VARCHAR NOT NULL,
            equipe_a_ids JSON NOT NULL,
            equipe_b_ids JSON NOT NULL,
            ratings_equipe_a_antes JSON NOT NULL,
            ratings_equipe_b_antes JSON NOT NULL,
            resultado_partida VARCHAR CHECK (resultado_partida IN ('win_a', 'win_b', 'draw')),
            ratings_equipe_a_depois JSON NOT NULL,
            ratings_equipe_b_depois JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS pdf_metadata (
            id INTEGER,
            filename VARCHAR NOT NULL,
            download_date DATE NOT NULL,
            original_url TEXT NOT NULL,
            size_bytes BIGINT NOT NULL,
            sha256_hash CHAR(64) UNIQUE NOT NULL,
            archive_identifier VARCHAR,
            archive_url TEXT,
            upload_status VARCHAR DEFAULT 'pending' CHECK (upload_status IN ('pending', 'uploaded', 'failed')),
            upload_date TIMESTAMP,
            extraction_status VARCHAR DEFAULT 'pending' CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed')),
            decisions_extracted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS decisoes (
            id INTEGER,
            numero_processo VARCHAR NOT NULL, -- This will store UUIDs after PII changes
            pdf_source_id INTEGER,
            json_source_file VARCHAR,
            extraction_timestamp TIMESTAMP,
            polo_ativo JSON NOT NULL, -- JSON of UUIDs
            polo_passivo JSON NOT NULL, -- JSON of UUIDs
            advogados_polo_ativo JSON NOT NULL, -- JSON of UUIDs (for full lawyer strings)
            advogados_polo_passivo JSON NOT NULL, -- JSON of UUIDs (for full lawyer strings)
            tipo_decisao VARCHAR,
            resultado VARCHAR,
            data_decisao DATE,
            resumo TEXT,
            texto_completo TEXT,
            raw_json_data JSON, -- JSON of PII-replaced decision data
            processed_for_trueskill BOOLEAN DEFAULT FALSE,
            partida_id INTEGER,
            validation_status VARCHAR DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid')),
            validation_errors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS json_files (
            id INTEGER,
            filename VARCHAR NOT NULL UNIQUE,
            file_path VARCHAR NOT NULL,
            file_size_bytes BIGINT,
            sha256_hash CHAR(64),
            extraction_date DATE,
            source_pdf_filename VARCHAR,
            total_decisions INTEGER DEFAULT 0,
            valid_decisions INTEGER DEFAULT 0,
            processing_status VARCHAR DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'archived')),
            processed_at TIMESTAMP,
            error_message TEXT,
            archived_to_duckdb BOOLEAN DEFAULT FALSE,
            original_file_deleted BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS pdfs (
            id INTEGER PRIMARY KEY,
            filename VARCHAR NOT NULL,
            date_published DATE NOT NULL,
            sha256_hash CHAR(64) UNIQUE NOT NULL,
            ia_identifier VARCHAR UNIQUE,
            ia_url TEXT,
            upload_status VARCHAR DEFAULT 'pending' CHECK (upload_status IN ('pending', 'uploaded', 'failed')),
            upload_date TIMESTAMP,
            file_size_bytes BIGINT, -- This column was added in 003, ensure it's here
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            -- Columns from 003 migration for pdfs table
            discovery_queue_id INTEGER,
            download_duration_ms INTEGER,
            processing_status TEXT DEFAULT 'pending'
        );""",
        # Indexes from 001_init.sql
        "CREATE INDEX IF NOT EXISTS idx_partidas_data ON partidas(data_partida);",
        "CREATE INDEX IF NOT EXISTS idx_partidas_processo ON partidas(numero_processo);",
        "CREATE INDEX IF NOT EXISTS idx_pdf_metadata_hash ON pdf_metadata(sha256_hash);",
        "CREATE INDEX IF NOT EXISTS idx_pdf_metadata_date ON pdf_metadata(download_date);",
        "CREATE INDEX IF NOT EXISTS idx_decisoes_processo ON decisoes(numero_processo);",
        "CREATE INDEX IF NOT EXISTS idx_decisoes_pdf ON decisoes(pdf_source_id);",
        "CREATE INDEX IF NOT EXISTS idx_decisoes_trueskill ON decisoes(processed_for_trueskill);",
        "CREATE INDEX IF NOT EXISTS idx_json_files_status ON json_files(processing_status);",
        "CREATE INDEX IF NOT EXISTS idx_pdfs_hash ON pdfs(sha256_hash);",
        "CREATE INDEX IF NOT EXISTS idx_pdfs_date ON pdfs(date_published);",
        # Views from 001_init.sql (and updated in 002)
        # The estatisticas_gerais view is updated in 002, so we use the 002 version.
        # ranking_atual view from 001:
        """CREATE OR REPLACE VIEW ranking_atual AS
            SELECT
                advogado_id, mu, sigma, mu - 3 * sigma as conservative_skill,
                total_partidas,
                ROW_NUMBER() OVER (ORDER BY mu DESC) as ranking_mu,
                ROW_NUMBER() OVER (ORDER BY mu - 3 * sigma DESC) as ranking_conservative
            FROM ratings WHERE total_partidas > 0 ORDER BY mu DESC;
        """,
        # From 002_archived_databases.sql
        """CREATE TABLE IF NOT EXISTS archived_databases (
            id INTEGER PRIMARY KEY,
            snapshot_date DATE NOT NULL,
            archive_type VARCHAR(20) NOT NULL CHECK (archive_type IN ('weekly', 'monthly', 'quarterly')),
            ia_identifier VARCHAR(100) NOT NULL UNIQUE,
            ia_url TEXT NOT NULL,
            file_size_bytes BIGINT NOT NULL,
            sha256_hash CHAR(64) NOT NULL,
            total_lawyers INTEGER,
            total_matches INTEGER,
            total_decisions INTEGER,
            upload_status VARCHAR(20) DEFAULT 'pending' CHECK (upload_status IN ('pending', 'uploading', 'completed', 'failed')),
            upload_started_at TIMESTAMP,
            upload_completed_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        "CREATE INDEX IF NOT EXISTS idx_archived_databases_date ON archived_databases(snapshot_date);",
        "CREATE INDEX IF NOT EXISTS idx_archived_databases_type ON archived_databases(archive_type);",
        "CREATE INDEX IF NOT EXISTS idx_archived_databases_status ON archived_databases(upload_status);",
        "CREATE INDEX IF NOT EXISTS idx_archived_databases_ia_id ON archived_databases(ia_identifier);",
        # estatisticas_gerais view from 002 (this replaces the one from 001)
        """CREATE OR REPLACE VIEW estatisticas_gerais AS
            SELECT
                (SELECT COUNT(*) FROM ratings) as total_advogados,
                (SELECT COUNT(*) FROM ratings WHERE total_partidas > 0) as advogados_ativos,
                (SELECT AVG(mu) FROM ratings WHERE total_partidas > 0) as mu_medio,
                (SELECT AVG(sigma) FROM ratings WHERE total_partidas > 0) as sigma_medio,
                (SELECT MAX(total_partidas) FROM ratings) as max_partidas,
                (SELECT COUNT(*) FROM partidas) as total_partidas,
                (SELECT COUNT(*) FROM pdf_metadata) as total_pdfs, /* This table might be deprecated by 'pdfs' */
                (SELECT COUNT(*) FROM pdf_metadata WHERE upload_status = 'uploaded') as pdfs_arquivados,
                (SELECT COUNT(*) FROM decisoes) as total_decisoes,
                (SELECT COUNT(*) FROM decisoes WHERE validation_status = 'valid') as decisoes_validas,
                (SELECT COUNT(*) FROM json_files) as total_json_files, /* This table might be deprecated */
                (SELECT COUNT(*) FROM json_files WHERE processing_status = 'completed') as json_files_processados,
                (SELECT COUNT(*) FROM pdfs) as total_pdfs_ia,
                (SELECT COUNT(*) FROM pdfs WHERE upload_status = 'uploaded') as pdfs_ia_uploaded,
                (SELECT COUNT(*) FROM archived_databases) as total_database_archives,
                (SELECT COUNT(*) FROM archived_databases WHERE upload_status = 'completed') as database_archives_completed,
                (SELECT MAX(snapshot_date) FROM archived_databases WHERE upload_status = 'completed') as latest_archive_date;
        """,
        # archive_status view from 002
        """CREATE OR REPLACE VIEW archive_status AS
            SELECT
                snapshot_date, archive_type, ia_identifier, ia_url,
                ROUND(file_size_bytes / 1024.0 / 1024.0, 2) as file_size_mb,
                total_lawyers, total_matches, total_decisions, upload_status, upload_completed_at,
                CASE WHEN upload_completed_at IS NOT NULL THEN
                    ROUND(EXTRACT('epoch' FROM upload_completed_at - upload_started_at) / 60.0, 1)
                ELSE NULL END as upload_duration_minutes,
                created_at
            FROM archived_databases ORDER BY snapshot_date DESC;
        """,
        # From 003_queue_system.sql
        """CREATE TABLE IF NOT EXISTS pdf_discovery_queue (
            id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, date TEXT NOT NULL, number TEXT, year INTEGER NOT NULL,
            status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
            priority INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0, last_attempt TIMESTAMP, error_message TEXT,
            metadata JSON, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS pdf_archive_queue (
            id INTEGER PRIMARY KEY, pdf_id INTEGER NOT NULL, local_path TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
            attempts INTEGER DEFAULT 0, last_attempt TIMESTAMP, error_message TEXT, ia_url TEXT, ia_item_id TEXT,
            upload_size_bytes INTEGER, upload_duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS pdf_extraction_queue (
            id INTEGER PRIMARY KEY, pdf_id INTEGER NOT NULL, local_path TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
            attempts INTEGER DEFAULT 0, last_attempt TIMESTAMP, error_message TEXT, extraction_result JSON,
            decisions_found INTEGER DEFAULT 0, processing_duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS rating_processing_queue (
            id INTEGER PRIMARY KEY, pdf_id INTEGER NOT NULL,
            status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
            attempts INTEGER DEFAULT 0, last_attempt TIMESTAMP, error_message TEXT,
            decisions_processed INTEGER DEFAULT 0, ratings_updated INTEGER DEFAULT 0, matches_created INTEGER DEFAULT 0,
            processing_duration_ms INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS queue_processing_log (
            id INTEGER PRIMARY KEY, queue_type TEXT NOT NULL, queue_item_id INTEGER NOT NULL, action TEXT NOT NULL,
            message TEXT, processing_duration_ms INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        # Indexes from 003
        "CREATE INDEX IF NOT EXISTS idx_discovery_queue_status_priority ON pdf_discovery_queue(status, priority DESC);",
        "CREATE INDEX IF NOT EXISTS idx_discovery_queue_date ON pdf_discovery_queue(date);",
        "CREATE INDEX IF NOT EXISTS idx_discovery_queue_year ON pdf_discovery_queue(year);",
        "CREATE INDEX IF NOT EXISTS idx_discovery_queue_url ON pdf_discovery_queue(url);",
        "CREATE INDEX IF NOT EXISTS idx_archive_queue_status ON pdf_archive_queue(status);",
        "CREATE INDEX IF NOT EXISTS idx_archive_queue_pdf_id ON pdf_archive_queue(pdf_id);",
        "CREATE INDEX IF NOT EXISTS idx_extraction_queue_status ON pdf_extraction_queue(status);",
        "CREATE INDEX IF NOT EXISTS idx_extraction_queue_pdf_id ON pdf_extraction_queue(pdf_id);",
        "CREATE INDEX IF NOT EXISTS idx_rating_queue_status ON rating_processing_queue(status);",
        "CREATE INDEX IF NOT EXISTS idx_rating_queue_pdf_id ON rating_processing_queue(pdf_id);",
        "CREATE INDEX IF NOT EXISTS idx_processing_log_queue_type ON queue_processing_log(queue_type);",
        "CREATE INDEX IF NOT EXISTS idx_processing_log_created_at ON queue_processing_log(created_at);",
        # Views from 003
        """CREATE VIEW IF NOT EXISTS queue_summary AS
            SELECT 'discovery' as queue_type, COUNT(*) as total_items, SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed, MIN(created_at) as oldest_item, MAX(created_at) as newest_item FROM pdf_discovery_queue
            UNION ALL SELECT 'archive' as queue_type, COUNT(*) as total_items, SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed, MIN(created_at) as oldest_item, MAX(created_at) as newest_item FROM pdf_archive_queue
            UNION ALL SELECT 'extraction' as queue_type, COUNT(*) as total_items, SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed, MIN(created_at) as oldest_item, MAX(created_at) as newest_item FROM pdf_extraction_queue
            UNION ALL SELECT 'ratings' as queue_type, COUNT(*) as total_items, SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed, SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed, MIN(created_at) as oldest_item, MAX(created_at) as newest_item FROM rating_processing_queue;
        """,
        """CREATE VIEW IF NOT EXISTS failed_queue_items AS
            SELECT 'discovery' as queue_type, id, date as item_date, url as item_identifier, attempts, error_message, last_attempt, created_at FROM pdf_discovery_queue WHERE status = 'failed'
            UNION ALL SELECT 'archive' as queue_type, aq.id, p.date_published as item_date, aq.local_path as item_identifier, aq.attempts, aq.error_message, aq.last_attempt, aq.created_at FROM pdf_archive_queue aq JOIN pdfs p ON aq.pdf_id = p.id WHERE aq.status = 'failed'
            UNION ALL SELECT 'extraction' as queue_type, eq.id, p.date_published as item_date, eq.local_path as item_identifier, eq.attempts, eq.error_message, eq.last_attempt, eq.created_at FROM pdf_extraction_queue eq JOIN pdfs p ON eq.pdf_id = p.id WHERE eq.status = 'failed'
            UNION ALL SELECT 'ratings' as queue_type, rq.id, p.date_published as item_date, CAST(rq.pdf_id AS TEXT) as item_identifier, rq.attempts, rq.error_message, rq.last_attempt, rq.created_at FROM rating_processing_queue rq JOIN pdfs p ON rq.pdf_id = p.id WHERE rq.status = 'failed'
            ORDER BY last_attempt DESC;
        """,
        # From 004_pii_decode_map.sql - Making pii_uuid the PRIMARY KEY
        """CREATE TABLE IF NOT EXISTS pii_decode_map (
            pii_uuid VARCHAR(36) PRIMARY KEY,
            original_value TEXT NOT NULL,
            value_for_uuid_ref TEXT NOT NULL,
            pii_type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        # Index on pii_uuid is created by PRIMARY KEY. Index on ref_type is still useful.
        "CREATE INDEX IF NOT EXISTS idx_pii_decode_map_ref_type ON pii_decode_map(value_for_uuid_ref, pii_type);",
        # Schema version table (manual management if needed, or remove if not versioning at all)
        """CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY, name VARCHAR NOT NULL, description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""
        # Note: The job_queue table is defined in models/diario.py's CausaGanhaDB methods
        # It is not part of the SCHEMA_STATEMENTS here. If it should be, it needs to be added.
        # For now, assuming its creation is handled elsewhere or not part of this core schema setup.
        # Let's add it for completeness if it's a core table.
        # It seems `queue_diario` in this file tries to insert into `job_queue`.
        # This table is NOT defined in any of the migrations 001-004.
        # This is a pre-existing issue. I will add its definition here based on its usage.
        """CREATE TABLE IF NOT EXISTS job_queue (
            url TEXT PRIMARY KEY,
            date TEXT,
            tribunal TEXT,
            filename TEXT,
            metadata JSON,
            status TEXT,
            ia_identifier TEXT,
            arquivo_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
    ]

    def __init__(self, db_path: Path = Path("data/causaganha.duckdb")):
        self.db_path = db_path
        self.conn = None
        # The 'migrations' directory is no longer needed for schema setup
        # self.migrations_dir = Path(__file__).resolve().parent.parent / "migrations"

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _create_tables_if_not_exist(self):
        """Creates all tables defined in SCHEMA_STATEMENTS if they don't exist."""
        if not self.conn:
            logger.error("Database connection not established. Cannot create tables.")
            raise ConnectionError("Database connection not established.")
        try:
            for stmt_idx, statement in enumerate(self.SCHEMA_STATEMENTS):
                logger.debug(
                    f"Executing schema statement {stmt_idx + 1}/{len(self.SCHEMA_STATEMENTS)}: {statement[:100]}..."
                )
                self.conn.execute(statement)
            self.conn.commit()  # Ensure all schema changes are committed
            logger.info("All schema statements executed successfully.")
        except Exception as e:
            logger.error(f"Error executing schema statement: {e}", exc_info=True)
            # Attempt to rollback if transaction was started by execute many, though DuckDB DDL is often auto-committed
            try:
                self.conn.rollback()
            except Exception as rb_e:
                logger.error(f"Rollback failed after schema error: {rb_e}")
            raise

    def connect(self):
        """Conecta ao banco DuckDB e cria tabelas se não existirem."""
        try:
            logger.info(f"Connecting to DuckDB: {self.db_path}")
            self.conn = duckdb.connect(str(self.db_path))
            logger.info(
                f"Connected to DuckDB: {self.db_path}. Ensuring schema exists..."
            )
            self._create_tables_if_not_exist()  # Create all tables directly
            logger.info("Schema setup complete.")
        except Exception as e:
            logger.error(
                f"Failed to connect or setup schema for DB {self.db_path}: {e}",
                exc_info=True,
            )
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
            self.conn = None
            raise

    def close(self):
        """Fecha conexão com banco."""
        if self.conn:
            logger.info(f"Closing connection to DuckDB: {self.db_path}")
            self.conn.close()
            self.conn = None

    # _run_migrations method is now removed.

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
        """Atualiza rating de um advogado. advogado_id is now expected to be a UUID."""
        existing = self.get_rating(advogado_id)  # advogado_id is UUID

        if existing:
            if increment_partidas:
                sql = """
                    UPDATE ratings SET
                        mu = ?, sigma = ?, total_partidas = total_partidas + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE advogado_id = ?
                """
                self.conn.execute(sql, [mu, sigma, advogado_id])
            else:
                sql = """
                    UPDATE ratings SET mu = ?, sigma = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE advogado_id = ?
                """
                self.conn.execute(sql, [mu, sigma, advogado_id])
        else:
            total_partidas = 1 if increment_partidas else 0
            sql = """
                INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            self.conn.execute(sql, [advogado_id, mu, sigma, total_partidas])
        self.conn.commit()

    def get_rating(self, advogado_id: str) -> Optional[Dict]:
        """Retorna rating específico de um advogado. advogado_id is UUID."""
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

    # =====================================
    # MÉTODOS: Partidas
    # =====================================

    def add_partida(
        self,
        data_partida: str,
        numero_processo: str,  # This will be a UUID
        equipe_a_ids: List[str],  # List of lawyer UUIDs
        equipe_b_ids: List[str],  # List of lawyer UUIDs
        ratings_antes_a: Dict[str, tuple],  # Keys are lawyer UUIDs
        ratings_antes_b: Dict[str, tuple],  # Keys are lawyer UUIDs
        resultado: str,
        ratings_depois_a: Dict[str, tuple],  # Keys are lawyer UUIDs
        ratings_depois_b: Dict[str, tuple],  # Keys are lawyer UUIDs
    ) -> int:
        """Adiciona nova partida e retorna ID. numero_processo and lawyer IDs are UUIDs."""
        max_id_result = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM partidas"
        ).fetchone()
        next_id = (
            max_id_result[0] if max_id_result and max_id_result[0] is not None else 1
        )

        sql = """
            INSERT INTO partidas (
                id, data_partida, numero_processo, equipe_a_ids, equipe_b_ids,
                ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
                ratings_equipe_a_depois, ratings_equipe_b_depois, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        try:
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
            self.conn.commit()
            return next_id
        except Exception as e:
            logger.error(
                f"Error adding partida for numero_processo {numero_processo}: {e}",
                exc_info=True,
            )
            try:
                self.conn.rollback()
            except Exception as rb_e:
                logger.error(f"Rollback failed after add_partida error: {rb_e}")
            raise

    def get_partidas(self, limit: int = None) -> pd.DataFrame:
        sql = "SELECT * FROM partidas ORDER BY data_partida DESC"
        if limit:
            sql += f" LIMIT {limit}"
        return self.conn.execute(sql).df()

    # =====================================
    # MÉTODOS: Decisões (PII-replaced)
    # =====================================
    def add_raw_decision(
        self,
        numero_processo_uuid: str,
        polo_ativo_uuids_json: str,
        polo_passivo_uuids_json: str,
        advogados_polo_ativo_full_str_uuids_json: str,
        advogados_polo_passivo_full_str_uuids_json: str,
        resultado_original: Optional[str],
        data_decisao_original: Optional[str],
        raw_json_pii_replaced: str,
        pdf_source_file: Optional[
            str
        ] = None,  # This might map to json_source_file if pdf filename is in json
        json_source_file: Optional[str] = None,
        tipo_decisao: Optional[str] = None,
        resumo_original: Optional[str] = None,
        texto_completo_original: Optional[str] = None,
        validation_status: str = "pending",
        validation_errors: Optional[str] = None,
        extraction_timestamp: Optional[str] = None,
        pdf_source_id: Optional[int] = None,
        partida_id: Optional[int] = None,
    ):
        max_id_result = self.conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM decisoes"
        ).fetchone()
        next_id = (
            max_id_result[0] if max_id_result and max_id_result[0] is not None else 1
        )

        current_ts_iso = extraction_timestamp
        if current_ts_iso is None:
            from datetime import datetime, timezone

            current_ts_iso = datetime.now(timezone.utc).isoformat()

        sql = """
            INSERT INTO decisoes (
                id, numero_processo, pdf_source_id, json_source_file, extraction_timestamp,
                polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo,
                tipo_decisao, resultado, data_decisao, resumo, texto_completo,
                raw_json_data, processed_for_trueskill, partida_id,
                validation_status, validation_errors, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        try:
            params = [
                next_id,
                numero_processo_uuid,
                pdf_source_id,
                json_source_file,
                current_ts_iso,
                polo_ativo_uuids_json,
                polo_passivo_uuids_json,
                advogados_polo_ativo_full_str_uuids_json,
                advogados_polo_passivo_full_str_uuids_json,
                tipo_decisao,
                resultado_original,
                data_decisao_original,
                resumo_original,
                texto_completo_original,
                raw_json_pii_replaced,
                False,
                partida_id,
                validation_status,
                validation_errors,
            ]
            self.conn.execute(sql, params)
            self.conn.commit()
            logger.info(
                f"Added decision ID {next_id} (processo_uuid: {numero_processo_uuid}) to 'decisoes'."
            )
            return next_id
        except Exception as e:
            logger.error(
                f"Error adding decision for {numero_processo_uuid} to 'decisoes': {e}",
                exc_info=True,
            )
            try:
                self.conn.rollback()
            except Exception as rb_e:
                logger.error(f"Rollback failed after add_raw_decision error: {rb_e}")
            raise

    # =====================================
    # MÉTODOS: Estatísticas e Views
    # =====================================

    def get_ranking(self, limit: int = 20) -> pd.DataFrame:
        return self.conn.execute(f"SELECT * FROM ranking_atual LIMIT {limit}").df()

    def get_statistics(self) -> Dict:
        # This method might need adjustment if the 'estatisticas_gerais' view is complex or changes.
        # For now, assume it exists and returns expected columns.
        try:
            result = self.conn.execute("SELECT * FROM estatisticas_gerais").fetchone()
            if not result:
                return {}
            # Get column names from cursor description
            colnames = [desc[0] for desc in self.conn.description]
            return dict(zip(colnames, result))
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}", exc_info=True)
            return {}

    # =====================================
    # MÉTODOS: Backup e Utilitários
    # =====================================

    def export_to_csv(self, output_dir: Path):
        output_dir.mkdir(exist_ok=True)
        # Added pii_decode_map to tables to export
        tables_to_export = [
            "ratings",
            "partidas",
            "pdf_metadata",
            "decisoes",
            "json_files",
            "pii_decode_map",
            "pdfs",
            "archived_databases",
            "pdf_discovery_queue",
            "pdf_archive_queue",
            "pdf_extraction_queue",
            "rating_processing_queue",
            "queue_processing_log",
        ]

        existing_tables = [
            row[0] for row in self.conn.execute("SHOW TABLES").fetchall()
        ]

        for table in tables_to_export:
            if table in existing_tables:
                try:
                    df = self.conn.execute(f"SELECT * FROM {table}").df()
                    df.to_csv(output_dir / f"{table}.csv", index=False)
                    logger.info("Tabela %s exportada: %d registros", table, len(df))
                except Exception as e:
                    logger.error(f"Failed to export table {table}: {e}", exc_info=True)
            else:
                logger.warning(f"Table {table} not found for export, skipping.")
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
            logger.error("Database export failed: %s", e, exc_info=True)
            return False

    def get_archive_statistics(
        self,
    ) -> Dict[str, Any]:  # Kept for compatibility, relies on get_statistics
        return self.get_statistics()

    def vacuum(self):
        self.conn.execute("VACUUM")
        self.conn.commit()
        logger.info("Database vacuum concluído")

    def get_db_info(self) -> Dict:
        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        size_mb = size_bytes / (1024 * 1024)
        return {
            "db_path": str(self.db_path),
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2),
            "tables": self._get_table_info(),
        }

    def _get_table_info(self) -> Dict:
        tables_info = {}
        try:
            all_db_tables = [
                row[0] for row in self.conn.execute("SHOW TABLES").fetchall()
            ]
            for table_name in all_db_tables:
                try:
                    count = self.conn.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    tables_info[table_name] = count
                except Exception as e:
                    tables_info[table_name] = f"Error counting: {e}"
        except Exception as e:
            logger.error(f"Could not SHOW TABLES: {e}", exc_info=True)
        return tables_info

    # Diario dataclass support methods (from original file, ensure they use self.conn.commit() if needed)
    def queue_diario(self, diario) -> bool:
        try:
            from models.diario import Diario

            if not isinstance(diario, Diario):
                raise ValueError("Expected Diario object")
            item = diario.queue_item
            self.conn.execute(
                "INSERT INTO job_queue (url, date, tribunal, filename, metadata, status, ia_identifier, arquivo_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (url) DO UPDATE SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP",
                [
                    item["url"],
                    item["date"],
                    item["tribunal"],
                    item["filename"],
                    json.dumps(item["metadata"]),
                    item["status"],
                    item["ia_identifier"],
                    item["arquivo_path"],
                ],
            )
            self.conn.commit()
            logger.info(f"Queued diario: {diario.display_name}")
            return True
        except Exception as e:
            logger.error(
                f"Error queuing diario {getattr(diario, 'display_name', 'unknown')}: {e}",
                exc_info=True,
            )
            return False

    def get_diarios_by_status(self, status: str) -> List:
        # This is a read-only method, no commit needed
        try:
            from models.diario import Diario

            # Construct column names from a sample Diario object or define explicitly
            # Assuming Diario.from_queue_item can handle dicts from zip(colnames, row)
            cursor = self.conn.execute(
                "SELECT url, date, tribunal, filename, metadata, status, ia_identifier, arquivo_path "
                "FROM job_queue WHERE status = ? ORDER BY created_at",
                [status],
            )
            colnames = [desc[0] for desc in cursor.description]
            diarios = [
                Diario.from_queue_item(dict(zip(colnames, row)))
                for row in cursor.fetchall()
            ]
            logger.info(f"Retrieved {len(diarios)} diarios with status '{status}'")
            return diarios
        except Exception as e:
            logger.error(
                f"Error retrieving diarios with status '{status}': {e}", exc_info=True
            )
            return []

    def update_diario_status(self, diario, new_status: str, **kwargs) -> bool:
        try:
            url = diario.url if hasattr(diario, "url") else str(diario)
            update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            values = [new_status]
            field_mappings = {
                "ia_identifier": "ia_identifier",
                "arquivo_path": "arquivo_path",
                "pdf_path": "arquivo_path",
                "error_message": "error_message",
            }
            for key, value in kwargs.items():
                if key in field_mappings:
                    update_fields.append(f"{field_mappings[key]} = ?")
                    values.append(str(value) if value else None)
            query = f"UPDATE job_queue SET {', '.join(update_fields)} WHERE url = ?"
            values.append(url)
            result = self.conn.execute(query, values)
            self.conn.commit()
            if result.rowcount > 0:
                logger.info(f"Updated diario status: {url} -> {new_status}")
                return True
            logger.warning(f"No diario found with URL for status update: {url}")
            return False
        except Exception as e:
            logger.error(
                f"Error updating diario status for {getattr(diario, 'url', diario)}: {e}",
                exc_info=True,
            )
            return False

    def get_diarios_by_tribunal(self, tribunal: str) -> List:
        # Read-only, no commit
        try:
            from models.diario import Diario

            cursor = self.conn.execute(
                "SELECT url, date, tribunal, filename, metadata, status, ia_identifier, arquivo_path "
                "FROM job_queue WHERE tribunal = ? ORDER BY date DESC",
                [tribunal],
            )
            colnames = [desc[0] for desc in cursor.description]
            diarios = [
                Diario.from_queue_item(dict(zip(colnames, row)))
                for row in cursor.fetchall()
            ]
            logger.info(f"Retrieved {len(diarios)} diarios for tribunal '{tribunal}'")
            return diarios
        except Exception as e:
            logger.error(
                f"Error retrieving diarios for tribunal '{tribunal}': {e}",
                exc_info=True,
            )
            return []

    def get_diario_statistics(self) -> Dict[str, Any]:
        # Read-only, no commit
        try:
            stats = {
                "total_diarios": self.conn.execute(
                    "SELECT COUNT(*) FROM job_queue"
                ).fetchone()[0]
            }
            status_res = self.conn.execute(
                "SELECT status, COUNT(*) FROM job_queue GROUP BY status ORDER BY COUNT(*) DESC"
            ).fetchall()
            stats["by_status"] = {status: count for status, count in status_res}
            tribunal_res = self.conn.execute(
                "SELECT tribunal, COUNT(*) FROM job_queue GROUP BY tribunal ORDER BY COUNT(*) DESC"
            ).fetchall()
            stats["by_tribunal"] = {tribunal: count for tribunal, count in tribunal_res}
            recent_res = self.conn.execute(
                "SELECT COUNT(*) FROM job_queue WHERE created_at >= CURRENT_DATE - INTERVAL 7 DAY"
            ).fetchone()
            stats["recent_activity"] = recent_res[0] if recent_res else 0
            return stats
        except Exception as e:
            logger.error(f"Error getting diario statistics: {e}", exc_info=True)
            return {}


# Removed MigrationRunner import and _run_migrations method.
# Schema creation is now handled by _create_tables_if_not_exist called from connect().
# Added .commit() to DML operations where appropriate.
# Made local imports of 'Diario' model in Diario support methods more consistent.
# Updated get_statistics to be more robust to view changes by fetching colnames from cursor.
# Updated _get_table_info to dynamically list tables.
# Updated export_to_csv to dynamically list tables and handle missing ones more gracefully.
