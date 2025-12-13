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
    hash VARCHAR(100),
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

-- Lawyer associations
CREATE TABLE IF NOT EXISTS intimation_lawyers (
    intimation_id BIGINT REFERENCES intimations(id),
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    lawyer_name VARCHAR(255),
    polo VARCHAR(1),

    PRIMARY KEY (intimation_id, oab_number, oab_state)
);

-- Parties
CREATE TABLE IF NOT EXISTS intimation_parties (
    id UUID PRIMARY KEY DEFAULT uuid(),
    intimation_id BIGINT REFERENCES intimations(id),
    party_name VARCHAR(255) NOT NULL,
    polo VARCHAR(1),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Decision analysis
CREATE TABLE IF NOT EXISTS decision_analysis (
    id UUID PRIMARY KEY DEFAULT uuid(),
    intimation_id BIGINT REFERENCES intimations(id),

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
    confidence_score FLOAT,

    -- Model info
    model_used VARCHAR(50),
    model_provider VARCHAR(20),
    analysis_duration_seconds FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(intimation_id)
);

-- Lawyer ratings
CREATE TABLE IF NOT EXISTS lawyer_ratings (
    id UUID PRIMARY KEY DEFAULT uuid(),
    oab_number VARCHAR(20) NOT NULL,
    oab_state VARCHAR(2) NOT NULL,
    lawyer_name VARCHAR(255),

    -- OpenSkill parameters
    mu FLOAT NOT NULL DEFAULT 25.0,
    sigma FLOAT NOT NULL DEFAULT 8.333,

    -- Statistics
    total_cases INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,

    -- Context
    tribunal VARCHAR(10),  -- NULL for global rating

    last_updated TIMESTAMP DEFAULT NOW(),

    UNIQUE(oab_number, oab_state, tribunal)
);

-- Sync log
CREATE TABLE IF NOT EXISTS sync_log (
    id UUID PRIMARY KEY DEFAULT uuid(),
    job_type VARCHAR(20) NOT NULL,
    entity_id VARCHAR(100),

    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,

    items_processed INTEGER DEFAULT 0,
    items_succeeded INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,

    status VARCHAR(20) NOT NULL,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Pipeline state
CREATE TABLE IF NOT EXISTS pipeline_state (
    task_id VARCHAR,
    step VARCHAR,
    timestamp TIMESTAMP
);
