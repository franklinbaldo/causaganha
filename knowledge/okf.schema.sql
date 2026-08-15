CREATE TABLE "Fonte" (
    nome VARCHAR PRIMARY KEY
);

CREATE TABLE "Pipeline" (
    nome VARCHAR PRIMARY KEY,
    fonte VARCHAR REFERENCES "Fonte"(nome)
);
