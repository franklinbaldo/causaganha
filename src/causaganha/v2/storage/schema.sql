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
    intimation_id BIGINT REFERENCES intimations(id),
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

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_intimations_tribunal_date
    ON intimations(sigla_tribunal, data_disponibilizacao DESC);

-- DuckDB does not support partial indexes (WHERE clause in CREATE INDEX)
-- So we create a regular index instead
CREATE INDEX IF NOT EXISTS idx_intimations_unanalyzed
    ON intimations(analyzed, data_disponibilizacao);
