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
