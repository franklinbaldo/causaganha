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

-- Session-level state machine for the hourly Claude Code loop. The scaffold is
-- intentionally invalid at birth; repeated okf-parser checks reveal what the
-- round still needs to read, decide, prove, check, and hand off.
CREATE TABLE "AgentRun" (
    id VARCHAR PRIMARY KEY,
    started_at VARCHAR NOT NULL CHECK (length(trim(started_at)) > 0),
    completed_at VARCHAR NOT NULL CHECK (length(trim(completed_at)) > 0),
    branch_at_start VARCHAR NOT NULL CHECK (length(trim(branch_at_start)) > 0),
    commit_at_start VARCHAR NOT NULL CHECK (length(trim(commit_at_start)) > 0),

    claude_md_reading_id VARCHAR NOT NULL CHECK (length(trim(claude_md_reading_id)) > 0),
    issues_reading_id VARCHAR NOT NULL CHECK (length(trim(issues_reading_id)) > 0),
    prs_reading_id VARCHAR NOT NULL CHECK (length(trim(prs_reading_id)) > 0),
    okf_reading_id VARCHAR NOT NULL CHECK (length(trim(okf_reading_id)) > 0),

    goal_ids VARCHAR[] NOT NULL CHECK (array_length(goal_ids) > 0),
    primary_goal_id VARCHAR NOT NULL CHECK (length(trim(primary_goal_id)) > 0),
    considered_work VARCHAR[] NOT NULL CHECK (array_length(considered_work) > 0),
    selected_work VARCHAR NOT NULL CHECK (length(trim(selected_work)) > 0),
    expected_behavior VARCHAR NOT NULL CHECK (length(trim(expected_behavior)) > 0),

    entry_state VARCHAR NOT NULL CHECK (entry_state IN ('new', 'red', 'green', 'review', 'blocked')),
    target_state VARCHAR NOT NULL CHECK (target_state IN ('red', 'green', 'review', 'merged', 'unblocked')),

    decision_ids VARCHAR[] NOT NULL CHECK (array_length(decision_ids) > 0),
    evidence_ids VARCHAR[] NOT NULL CHECK (array_length(evidence_ids) > 0),
    check_ids VARCHAR[] NOT NULL CHECK (array_length(check_ids) > 0),
    result_state VARCHAR NOT NULL CHECK (result_state IN ('red', 'green', 'review', 'merged', 'blocked')),
    result_summary VARCHAR NOT NULL CHECK (length(trim(result_summary)) > 0),
    next_move VARCHAR NOT NULL CHECK (length(trim(next_move)) > 0)
);

CREATE TABLE "AgentReading" (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES "AgentRun"(id),
    subject VARCHAR NOT NULL CHECK (subject IN ('claude_md', 'open_issues', 'open_prs', 'okf_knowledge', 'code', 'tests', 'ci', 'other')),
    reference VARCHAR NOT NULL CHECK (length(trim(reference)) > 0),
    finding VARCHAR NOT NULL CHECK (length(trim(finding)) > 0)
);

CREATE TABLE "AgentGoal" (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES "AgentRun"(id),
    goal VARCHAR NOT NULL CHECK (length(trim(goal)) > 0),
    rationale VARCHAR NOT NULL CHECK (length(trim(rationale)) > 0),
    success_signal VARCHAR NOT NULL CHECK (length(trim(success_signal)) > 0),
    status VARCHAR NOT NULL CHECK (status IN ('proposed', 'active', 'achieved', 'carried'))
);

CREATE TABLE "AgentDecision" (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES "AgentRun"(id),
    goal_id VARCHAR REFERENCES "AgentGoal"(id),
    question VARCHAR NOT NULL CHECK (length(trim(question)) > 0),
    choice VARCHAR NOT NULL CHECK (length(trim(choice)) > 0),
    rationale VARCHAR NOT NULL CHECK (length(trim(rationale)) > 0)
);

CREATE TABLE "AgentEvidence" (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES "AgentRun"(id),
    goal_id VARCHAR REFERENCES "AgentGoal"(id),
    kind VARCHAR NOT NULL CHECK (kind IN ('test_red', 'test_green', 'ci', 'diff', 'review', 'runtime', 'issue', 'pr', 'okf', 'other')),
    reference VARCHAR NOT NULL CHECK (length(trim(reference)) > 0),
    summary VARCHAR NOT NULL CHECK (length(trim(summary)) > 0)
);

CREATE TABLE "AgentCheck" (
    id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL REFERENCES "AgentRun"(id),
    goal_id VARCHAR REFERENCES "AgentGoal"(id),
    command VARCHAR NOT NULL CHECK (length(trim(command)) > 0),
    result VARCHAR NOT NULL CHECK (result IN ('passed', 'failed', 'observed')),
    evidence_id VARCHAR REFERENCES "AgentEvidence"(id),
    summary VARCHAR NOT NULL CHECK (length(trim(summary)) > 0)
);
