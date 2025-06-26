-- Migration 001: Initial Schema
-- Creates all core tables, indexes, and views for CausaGanha
-- Date: 2025-06-26

-- Tabela ratings - TrueSkill ratings for lawyers
CREATE TABLE IF NOT EXISTS ratings (
    advogado_id VARCHAR PRIMARY KEY,
    mu DOUBLE NOT NULL DEFAULT 25.0,
    sigma DOUBLE NOT NULL DEFAULT 8.333,
    total_partidas INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela partidas - Match history between lawyer teams
CREATE TABLE IF NOT EXISTS partidas (
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
);

-- Tabela pdf_metadata - Metadata for downloaded PDF files
CREATE TABLE IF NOT EXISTS pdf_metadata (
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
);

-- Tabela decisoes - Extracted judicial decisions
CREATE TABLE IF NOT EXISTS decisoes (
    id INTEGER,
    numero_processo VARCHAR NOT NULL,
    pdf_source_id INTEGER,
    json_source_file VARCHAR,
    extraction_timestamp TIMESTAMP,
    polo_ativo JSON NOT NULL,
    polo_passivo JSON NOT NULL,
    advogados_polo_ativo JSON NOT NULL,
    advogados_polo_passivo JSON NOT NULL,
    tipo_decisao VARCHAR,
    resultado VARCHAR,
    data_decisao DATE,
    resumo TEXT,
    texto_completo TEXT,
    raw_json_data JSON,
    processed_for_trueskill BOOLEAN DEFAULT FALSE,
    partida_id INTEGER,
    validation_status VARCHAR DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid')),
    validation_errors TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela json_files - Processing metadata for JSON extraction files
CREATE TABLE IF NOT EXISTS json_files (
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
);

-- Tabela pdfs - Internet Archive metadata (NEW table for IA integration)
CREATE TABLE IF NOT EXISTS pdfs (
    id INTEGER PRIMARY KEY,
    filename VARCHAR NOT NULL,
    date_published DATE NOT NULL,
    sha256_hash CHAR(64) UNIQUE NOT NULL,
    ia_identifier VARCHAR UNIQUE,
    ia_url TEXT,
    upload_status VARCHAR DEFAULT 'pending' CHECK (upload_status IN ('pending', 'uploaded', 'failed')),
    upload_date TIMESTAMP,
    file_size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES for performance
CREATE INDEX IF NOT EXISTS idx_partidas_data ON partidas(data_partida);
CREATE INDEX IF NOT EXISTS idx_partidas_processo ON partidas(numero_processo);
CREATE INDEX IF NOT EXISTS idx_pdf_metadata_hash ON pdf_metadata(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_pdf_metadata_date ON pdf_metadata(download_date);
CREATE INDEX IF NOT EXISTS idx_decisoes_processo ON decisoes(numero_processo);
CREATE INDEX IF NOT EXISTS idx_decisoes_pdf ON decisoes(pdf_source_id);
CREATE INDEX IF NOT EXISTS idx_decisoes_trueskill ON decisoes(processed_for_trueskill);
CREATE INDEX IF NOT EXISTS idx_json_files_status ON json_files(processing_status);
CREATE INDEX IF NOT EXISTS idx_pdfs_hash ON pdfs(sha256_hash);
CREATE INDEX IF NOT EXISTS idx_pdfs_date ON pdfs(date_published);

-- VIEWS for analytics and reporting
CREATE OR REPLACE VIEW ranking_atual AS
SELECT 
    advogado_id,
    mu,
    sigma,
    mu - 3 * sigma as conservative_skill,
    total_partidas,
    ROW_NUMBER() OVER (ORDER BY mu DESC) as ranking_mu,
    ROW_NUMBER() OVER (ORDER BY mu - 3 * sigma DESC) as ranking_conservative
FROM ratings
WHERE total_partidas > 0
ORDER BY mu DESC;

CREATE OR REPLACE VIEW estatisticas_gerais AS
SELECT 
    (SELECT COUNT(*) FROM ratings) as total_advogados,
    (SELECT COUNT(*) FROM ratings WHERE total_partidas > 0) as advogados_ativos,
    (SELECT AVG(mu) FROM ratings WHERE total_partidas > 0) as mu_medio,
    (SELECT AVG(sigma) FROM ratings WHERE total_partidas > 0) as sigma_medio,
    (SELECT MAX(total_partidas) FROM ratings) as max_partidas,
    (SELECT COUNT(*) FROM partidas) as total_partidas,
    (SELECT COUNT(*) FROM pdf_metadata) as total_pdfs,
    (SELECT COUNT(*) FROM pdf_metadata WHERE upload_status = 'uploaded') as pdfs_arquivados,
    (SELECT COUNT(*) FROM decisoes) as total_decisoes,
    (SELECT COUNT(*) FROM decisoes WHERE validation_status = 'valid') as decisoes_validas,
    (SELECT COUNT(*) FROM json_files) as total_json_files,
    (SELECT COUNT(*) FROM json_files WHERE processing_status = 'completed') as json_files_processados,
    (SELECT COUNT(*) FROM pdfs) as total_pdfs_ia,
    (SELECT COUNT(*) FROM pdfs WHERE upload_status = 'uploaded') as pdfs_ia_uploaded;