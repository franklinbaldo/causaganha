CREATE TABLE "DocumentoProcesso" (
    fonte VARCHAR,
    id_documento VARCHAR,
    processo_nr VARCHAR,
    tipo VARCHAR,
    data VARCHAR,
    url VARCHAR,
    resumo VARCHAR,
    PRIMARY KEY (fonte, id_documento)
);
