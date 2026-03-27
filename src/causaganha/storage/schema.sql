-- Monitored courts
CREATE TABLE IF NOT EXISTS monitored_courts (
    sigla_tribunal VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Intimations metadata (from PJe API)
CREATE TABLE IF NOT EXISTS intimations (
    -- From API
    id BIGINT PRIMARY KEY,
    numero_processo VARCHAR(25) NOT NULL,
    numeroprocessocommascara VARCHAR(30),
    data_disponibilizacao DATE NOT NULL,
    sigla_tribunal VARCHAR(10) NOT NULL,
    id_orgao INTEGER,
    tipo_comunicacao VARCHAR(50),
    nome_orgao VARCHAR(255),
    texto TEXT,
    link VARCHAR(500),
    tipo_documento VARCHAR(100),
    nome_classe VARCHAR(255),
    codigo_classe VARCHAR(10),
    hash VARCHAR(100) UNIQUE,
    status VARCHAR(1),

    -- Archiving
    ia_url VARCHAR(500),

    -- Analysis tracking
    analyzed BOOLEAN DEFAULT FALSE,
    analysis_attempted_at TIMESTAMP,
    analysis_error TEXT,
    analyzed_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Lawyer associations (extracted from API destinatarioadvogados)
CREATE TABLE IF NOT EXISTS intimation_lawyers (
    intimation_id BIGINT,
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    lawyer_name VARCHAR(255),
    polo VARCHAR(1),  -- 'A' = autor, 'P' = réu, etc.

    PRIMARY KEY (intimation_id, oab_number, oab_state)
);

-- Decision analysis (from Pydantic AI)
CREATE TABLE IF NOT EXISTS decision_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intimation_id BIGINT UNIQUE,

    -- Winner info
    winner_lawyer_oab VARCHAR(20) NOT NULL,
    winner_lawyer_state VARCHAR(2) NOT NULL,
    winner_party_name VARCHAR(255),

    -- Loser info
    loser_lawyer_oab VARCHAR(20) NOT NULL,
    loser_lawyer_state VARCHAR(2) NOT NULL,
    loser_party_name VARCHAR(255),

    -- Decision details
    decision_type VARCHAR(50),
    outcome VARCHAR(50),
    judge_name VARCHAR(255),
    decision_reasoning TEXT,

    -- Quality metrics
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),

    -- Model info
    model_used VARCHAR(50),
    model_provider VARCHAR(20),
    analysis_duration_seconds FLOAT,

    -- Analysis tracking
    analysis_method VARCHAR(20) DEFAULT 'llm',
    rag_confidence FLOAT,
    rag_votes_json TEXT,  -- JSON string

    created_at TIMESTAMP DEFAULT NOW(),

    -- Status
    rated BOOLEAN DEFAULT FALSE,
    rated_at TIMESTAMP
);

-- Lawyer ratings (OpenSkill - existing, may need adjustments)
CREATE TABLE IF NOT EXISTS lawyer_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    lawyer_name VARCHAR(255),

    -- OpenSkill parameters
    mu FLOAT NOT NULL DEFAULT 25.0,
    sigma FLOAT NOT NULL DEFAULT 8.333,

    -- Derived rating (conservative estimate)
    rating FLOAT,

    -- Statistics
    total_cases INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    win_rate FLOAT,

    -- Context
    tribunal VARCHAR(10) DEFAULT 'GLOBAL',  -- 'GLOBAL' for global rating

    last_updated TIMESTAMP DEFAULT NOW(),

    UNIQUE(oab_number, oab_state, tribunal)
);

-- Rating history (OpenSkill snapshots per rated communication)
CREATE TABLE IF NOT EXISTS ratings_history (
    advogado_id VARCHAR NOT NULL,        -- UUIDv5 (OAB+UF)
    comunicacao_id VARCHAR NOT NULL,      -- UUIDv5 of the communication that triggered this update
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    mu_before FLOAT NOT NULL,
    sigma_before FLOAT NOT NULL,
    mu_after FLOAT NOT NULL,
    sigma_after FLOAT NOT NULL,
    rating_after FLOAT NOT NULL,         -- mu_after - 3 * sigma_after
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    rated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (advogado_id, comunicacao_id)
);

CREATE INDEX IF NOT EXISTS idx_ratings_history_advogado
    ON ratings_history(advogado_id, rated_at);

-- Classificacoes (outcome labels per unique text)
CREATE TABLE IF NOT EXISTS classificacoes (
    texto_id VARCHAR NOT NULL,
    metodo VARCHAR(30) NOT NULL,          -- 'llm', 'rag', 'hybrid', 'manual'
    outcome VARCHAR(50),                  -- 'procedente', 'improcedente', 'parcialmente procedente', 'unknown'
    decision_type VARCHAR(50),            -- 'sentença', 'acórdão', 'decisão interlocutória'
    winner_advogado_id VARCHAR,           -- UUIDv5 FK to advogados
    loser_advogado_id VARCHAR,            -- UUIDv5 FK to advogados
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
    classified_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (texto_id, metodo)
);

CREATE INDEX IF NOT EXISTS idx_classificacoes_outcome
    ON classificacoes(outcome);

-- Sync/processing log
CREATE TABLE IF NOT EXISTS sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(20) NOT NULL,  -- 'collect', 'analyze', 'score'
    entity_id VARCHAR(100),  -- tribunal or batch identifier

    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,

    items_processed INTEGER DEFAULT 0,
    items_succeeded INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,

    status VARCHAR(20) NOT NULL,  -- 'running', 'success', 'failed', 'partial'
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Parquet export tracking (for Internet Archive archival)
CREATE TABLE IF NOT EXISTS parquet_exports (
    tribunal VARCHAR(10) NOT NULL,
    partition_date DATE NOT NULL,
    ia_item_id VARCHAR NOT NULL,
    ia_url VARCHAR NOT NULL,
    parquet_filename VARCHAR NOT NULL,
    row_count INTEGER,
    file_size_mb FLOAT,
    uploaded_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,  -- 'pending', 'completed', 'failed'
    error_message TEXT,

    PRIMARY KEY (tribunal, partition_date),
    UNIQUE (ia_item_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_intimations_tribunal_date
    ON intimations(sigla_tribunal, data_disponibilizacao DESC);

-- DuckDB does not support partial indexes (WHERE clause in CREATE INDEX)
-- So we create a regular index instead
CREATE INDEX IF NOT EXISTS idx_intimations_unanalyzed
    ON intimations(analyzed, data_disponibilizacao);

CREATE INDEX IF NOT EXISTS idx_lawyer_ratings_ranking
    ON lawyer_ratings(tribunal, rating DESC);

CREATE INDEX IF NOT EXISTS idx_decision_analysis_rated
    ON decision_analysis(rated, created_at);

CREATE INDEX IF NOT EXISTS idx_parquet_exports_status
    ON parquet_exports(status);

CREATE INDEX IF NOT EXISTS idx_parquet_exports_date
    ON parquet_exports(partition_date DESC);
-- Archival log to track cold storage tarballs
CREATE TABLE IF NOT EXISTS archival_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tribunal VARCHAR(10) NOT NULL,
    archive_year INTEGER NOT NULL,
    archive_month INTEGER NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'archived', -- 'archived', 'restoring', 'restored'
    file_count INTEGER,
    total_size_mb FLOAT,
    archived_at TIMESTAMP DEFAULT NOW(),
    restored_at TIMESTAMP,
    UNIQUE (tribunal, archive_year, archive_month)
);

CREATE INDEX IF NOT EXISTS idx_archival_log_date
    ON archival_log(archive_year DESC, archive_month DESC);

-- Audit log for LGPD compliance tracking
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_identifier VARCHAR(255) NOT NULL, -- IP, email, or token ID
    action_type VARCHAR(50) NOT NULL,      -- 'access_dashboard', 'export_data', 'api_query'
    resource_accessed TEXT NOT NULL,       -- e.g., 'Tribunal TJSP, Filters: Date Range'
    accessed_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_date
    ON audit_log(accessed_at DESC);
