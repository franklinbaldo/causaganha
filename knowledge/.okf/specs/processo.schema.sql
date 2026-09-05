CREATE TABLE "Processo" (
    nr_processo VARCHAR PRIMARY KEY,
    nr_processo_mascara VARCHAR,
    encontrado BOOLEAN,
    fontes_presentes VARCHAR[],
    djen_id VARCHAR,
    juris_id VARCHAR,
    stj_id VARCHAR,
    datajud_id VARCHAR,
    documentos_truncados BOOLEAN,
    dataset_gerado_em VARCHAR,
    avisos VARCHAR[]
);
