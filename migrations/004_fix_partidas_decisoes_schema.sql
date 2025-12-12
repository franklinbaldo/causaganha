-- Fix schema for partidas and decisoes tables with data preservation

-- Partidas Table
CREATE SEQUENCE IF NOT EXISTS partidas_id_seq;
CREATE TABLE partidas_new (
    id INTEGER PRIMARY KEY DEFAULT nextval('partidas_id_seq'),
    data_partida DATE,
    numero_processo TEXT,
    equipe_a_ids TEXT, -- JSON string
    equipe_b_ids TEXT, -- JSON string
    ratings_equipe_a_antes TEXT, -- JSON string
    ratings_equipe_b_antes TEXT, -- JSON string
    resultado_partida TEXT,
    ratings_equipe_a_depois TEXT, -- JSON string
    ratings_equipe_b_depois TEXT, -- JSON string
    decisao_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO partidas_new (
    id, data_partida, numero_processo, equipe_a_ids, equipe_b_ids,
    ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
    ratings_equipe_a_depois, ratings_equipe_b_depois, created_at
)
SELECT
    id, CAST(data_partida AS DATE), numero_processo, equipe_a_ids, equipe_b_ids,
    ratings_equipe_a_antes, ratings_equipe_b_antes, resultado_partida,
    ratings_equipe_a_depois, ratings_equipe_b_depois, created_at
FROM partidas;

SELECT setval('partidas_id_seq', COALESCE((SELECT MAX(id) FROM partidas_new), 0) + 1);

DROP TABLE partidas;
ALTER TABLE partidas_new RENAME TO partidas;


-- Decisoes Table
CREATE SEQUENCE IF NOT EXISTS decisoes_id_seq;
CREATE TABLE decisoes_new (
    id INTEGER PRIMARY KEY DEFAULT nextval('decisoes_id_seq'),
    numero_processo TEXT NOT NULL,
    json_source_file TEXT,
    ia_identifier TEXT,
    tipo_decisao TEXT,
    resultado TEXT,
    polo_ativo TEXT, -- JSON string
    polo_passivo TEXT, -- JSON string
    advogados_polo_ativo TEXT, -- JSON string
    advogados_polo_passivo TEXT, -- JSON string
    resumo TEXT,
    raw_json_data TEXT, -- JSON string
    processed_for_openskill BOOLEAN DEFAULT FALSE,
    validation_status TEXT DEFAULT 'pending',
    data_decisao DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO decisoes_new (
    id, numero_processo, json_source_file, tipo_decisao, resultado,
    polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo,
    raw_json_data, validation_status, data_decisao, created_at
)
SELECT
    id, numero_processo, json_source_file, tipo_decisao, resultado,
    polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo,
    raw_json_data, validation_status, CAST(data_decisao AS DATE), created_at
FROM decisoes;

SELECT setval('decisoes_id_seq', COALESCE((SELECT MAX(id) FROM decisoes_new), 0) + 1);

DROP TABLE decisoes;
ALTER TABLE decisoes_new RENAME TO decisoes;

CREATE INDEX idx_decisoes_numero_processo ON decisoes(numero_processo);
CREATE INDEX idx_decisoes_validation_status ON decisoes(validation_status);
