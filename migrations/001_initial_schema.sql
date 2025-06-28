-- migrations/001_initial_schema.sql

-- Ratings Table
CREATE TABLE IF NOT EXISTS ratings (
    advogado_id TEXT PRIMARY KEY,
    mu REAL,
    sigma REAL,
    total_partidas INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partidas Table
CREATE TABLE IF NOT EXISTS partidas (
    id INTEGER PRIMARY KEY,
    data_partida TEXT, -- Store as ISO date string e.g., YYYY-MM-DD
    numero_processo TEXT,
    equipe_a_ids TEXT, -- JSON string
    equipe_b_ids TEXT, -- JSON string
    ratings_equipe_a_antes TEXT, -- JSON string
    ratings_equipe_b_antes TEXT, -- JSON string
    resultado_partida TEXT,
    ratings_equipe_a_depois TEXT, -- JSON string
    ratings_equipe_b_depois TEXT, -- JSON string
    -- From original CLI _store_match_record, it also had decisao_id and created_at
    decisao_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PDF Metadata Table (simplified for now)
CREATE TABLE IF NOT EXISTS pdf_metadata (
    ia_identifier TEXT PRIMARY KEY,
    title TEXT,
    original_url TEXT UNIQUE, -- Added UNIQUE constraint based on typical usage
    file_name TEXT,           -- Often useful
    tribunal TEXT,            -- Often useful
    data_diario DATE,         -- Date of the "diario" itself
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    processing_status TEXT,   -- e.g., 'pending', 'analyzed', 'error'
    error_message TEXT,
    raw_metadata TEXT         -- JSON string for any other metadata
);

-- Decisoes Table
CREATE TABLE IF NOT EXISTS decisoes (
    id INTEGER PRIMARY KEY, -- Or use UUID if preferred for distributed generation
    numero_processo TEXT NOT NULL, -- Should probably be unique with other fields, or have its own unique ID
    json_source_file TEXT,
    ia_identifier TEXT, -- Link back to the PDF/Diario
    tipo_decisao TEXT,
    resultado TEXT,
    polo_ativo TEXT, -- JSON string
    polo_passivo TEXT, -- JSON string
    advogados_polo_ativo TEXT, -- JSON string
    advogados_polo_passivo TEXT, -- JSON string
    resumo TEXT,
    raw_json_data TEXT, -- JSON string
    processed_for_openskill BOOLEAN DEFAULT FALSE,
    validation_status TEXT DEFAULT 'pending', -- e.g., 'pending', 'valid', 'invalid', 'needs_review'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_decisoes_numero_processo ON decisoes(numero_processo);
CREATE INDEX IF NOT EXISTS idx_decisoes_validation_status ON decisoes(validation_status);


-- JSON Files Table (for storing raw JSON outputs from various sources)
CREATE TABLE IF NOT EXISTS json_files (
    filename TEXT PRIMARY KEY, -- e.g., path or unique ID for the JSON file
    content TEXT, -- JSON string
    source_type TEXT, -- e.g., 'gemini_extraction', 'manual_input'
    source_identifier TEXT, -- e.g., PDF filename, URL, ia_identifier it relates to
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_json_files_source_identifier ON json_files(source_identifier);

-- Job Queue Table (for Diario processing)
CREATE SEQUENCE IF NOT EXISTS job_queue_id_seq;
CREATE TABLE IF NOT EXISTS job_queue (
    id BIGINT PRIMARY KEY DEFAULT nextval('job_queue_id_seq'),
    url TEXT NOT NULL UNIQUE,
    date DATE, -- Date of the Diario publication
    tribunal TEXT,
    filename TEXT, -- Suggested filename for the Diario
    metadata TEXT, -- JSON string for additional metadata
    status TEXT DEFAULT 'pending', -- e.g., 'pending', 'downloaded', 'archived', 'analyzed', 'failed_download', etc.
    ia_identifier TEXT, -- Internet Archive identifier
    arquivo_path TEXT, -- Local path to the downloaded file, if any
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status);
CREATE INDEX IF NOT EXISTS idx_job_queue_tribunal_date ON job_queue(tribunal, date);

-- Add any necessary views that CausaGanhaDB might rely on (e.g., ranking_atual, estatisticas_gerais)
-- These were present in the original 001_init.sql.
-- For now, I'll add ranking_atual if it's simple and directly used by a tested method.
-- CausaGanhaDB.get_ranking() uses 'ranking_atual'
-- CausaGanhaDB.get_statistics() uses 'estatisticas_gerais'

CREATE VIEW IF NOT EXISTS ranking_atual AS
SELECT
    advogado_id,
    mu,
    sigma,
    total_partidas,
    (mu - 3 * sigma) AS conservative_skill -- Example conservative rating
FROM ratings
ORDER BY conservative_skill DESC;

-- A very basic estatisticas_gerais view. This would need to be expanded.
CREATE VIEW IF NOT EXISTS estatisticas_gerais AS
SELECT
    (SELECT COUNT(*) FROM ratings) AS total_advogados,
    (SELECT COUNT(*) FROM ratings WHERE total_partidas > 0) AS advogados_ativos,
    (SELECT AVG(mu) FROM ratings) AS mu_medio,
    (SELECT AVG(sigma) FROM ratings) AS sigma_medio,
    (SELECT MAX(total_partidas) FROM ratings) AS max_partidas,
    (SELECT COUNT(*) FROM partidas) AS total_partidas,
    (SELECT COUNT(*) FROM pdf_metadata) AS total_pdfs, -- Using pdf_metadata as a proxy for PDFs
    (SELECT COUNT(*) FROM pdf_metadata WHERE processing_status = 'archived' OR ia_identifier IS NOT NULL) AS pdfs_arquivados, -- Example logic
    (SELECT COUNT(*) FROM decisoes) AS total_decisoes,
    (SELECT COUNT(*) FROM decisoes WHERE validation_status = 'valid') AS decisoes_validas,
    (SELECT COUNT(*) FROM json_files) AS total_json_files,
    (SELECT COUNT(*) FROM json_files WHERE source_type = 'gemini_extraction') AS json_files_processados; -- Example logic
