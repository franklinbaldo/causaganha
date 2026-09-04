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
