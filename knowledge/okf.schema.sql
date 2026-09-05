CREATE TABLE "Fonte" (
    nome VARCHAR PRIMARY KEY
);

CREATE TABLE "Pipeline" (
    nome VARCHAR PRIMARY KEY,
    fonte VARCHAR REFERENCES "Fonte"(nome)
);

CREATE TABLE "DjenResumo" (
    id VARCHAR PRIMARY KEY,
    primeira_publicacao VARCHAR,
    ultima_publicacao VARCHAR,
    n_publicacoes BIGINT,
    tribunais VARCHAR[]
);

CREATE TABLE "JurisDecisao" (
    id VARCHAR PRIMARY KEY,
    n_documentos BIGINT,
    tipos VARCHAR[],
    data_julgamento VARCHAR,
    orgao VARCHAR,
    relator VARCHAR,
    classe VARCHAR,
    url VARCHAR
);

CREATE TABLE "StjAcordao" (
    id VARCHAR PRIMARY KEY,
    classe VARCHAR,
    relator VARCHAR,
    tema VARCHAR,
    tese VARCHAR,
    ementa VARCHAR,
    data_decisao VARCHAR,
    data_publicacao VARCHAR
);

CREATE TABLE "DatajudCapa" (
    id VARCHAR PRIMARY KEY,
    classe_oficial VARCHAR,
    assuntos VARCHAR,
    orgao_julgador VARCHAR,
    grau VARCHAR,
    data_ajuizamento VARCHAR,
    ultima_atualizacao VARCHAR
);

CREATE TABLE "Processo" (
    nr_processo VARCHAR PRIMARY KEY,
    nr_processo_mascara VARCHAR,
    encontrado BOOLEAN,
    fontes_presentes VARCHAR[],
    djen_id VARCHAR REFERENCES "DjenResumo"(id),
    juris_id VARCHAR REFERENCES "JurisDecisao"(id),
    stj_id VARCHAR REFERENCES "StjAcordao"(id),
    datajud_id VARCHAR REFERENCES "DatajudCapa"(id),
    documentos_truncados BOOLEAN,
    dataset_gerado_em VARCHAR,
    avisos VARCHAR[]
);

CREATE TABLE "FonteCobertura" (
    id VARCHAR PRIMARY KEY,
    processo_nr VARCHAR REFERENCES "Processo"(nr_processo),
    fonte VARCHAR,
    status VARCHAR,
    registros BIGINT
);

CREATE TABLE "DocumentoProcesso" (
    fonte VARCHAR,
    id_documento VARCHAR,
    processo_nr VARCHAR REFERENCES "Processo"(nr_processo),
    tipo VARCHAR,
    data VARCHAR,
    url VARCHAR,
    resumo VARCHAR,
    PRIMARY KEY (fonte, id_documento)
);

-- Operational contract for the hourly Claude Code loop.
-- A session starts from the scaffold in .claude/agent-run-scaffold.md and
-- becomes valid as the agent reads the project, chooses goals, advances work,
-- records evidence, and closes the round.
CREATE TABLE "AgentRun" (
    id VARCHAR PRIMARY KEY,
    started_at VARCHAR NOT NULL,
    completed_at VARCHAR NOT NULL,
    branch_at_start VARCHAR NOT NULL,
    commit_at_start VARCHAR NOT NULL,

    read_claude_md BOOLEAN NOT NULL CHECK (read_claude_md = TRUE),
    read_open_issues BOOLEAN NOT NULL CHECK (read_open_issues = TRUE),
    read_open_prs BOOLEAN NOT NULL CHECK (read_open_prs = TRUE),
    read_okf_knowledge BOOLEAN NOT NULL CHECK (read_okf_knowledge = TRUE),

    goals VARCHAR[] NOT NULL CHECK (array_length(goals) > 0),
    goal_rationale VARCHAR NOT NULL CHECK (length(trim(goal_rationale)) > 0),
    considered_work VARCHAR[] NOT NULL CHECK (array_length(considered_work) > 0),
    selected_work VARCHAR NOT NULL CHECK (length(trim(selected_work)) > 0),
    expected_behavior VARCHAR NOT NULL CHECK (length(trim(expected_behavior)) > 0),

    entry_state VARCHAR NOT NULL CHECK (entry_state IN ('new', 'red', 'green', 'review', 'blocked')),
    target_state VARCHAR NOT NULL CHECK (target_state IN ('red', 'green', 'review', 'merged', 'unblocked')),

    actions VARCHAR[] NOT NULL CHECK (array_length(actions) > 0),
    evidence VARCHAR[] NOT NULL CHECK (array_length(evidence) > 0),
    checks VARCHAR[] NOT NULL CHECK (array_length(checks) > 0),
    result_state VARCHAR NOT NULL CHECK (result_state IN ('red', 'green', 'review', 'merged', 'blocked')),
    result_summary VARCHAR NOT NULL CHECK (length(trim(result_summary)) > 0),
    next_move VARCHAR NOT NULL CHECK (length(trim(next_move)) > 0)
);
