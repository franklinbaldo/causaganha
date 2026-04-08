-- ============================================
-- CausaGanha Remote Catalog
<<<<<<< HEAD
-- Generated: 2026-03-30 22:34:44 UTC
=======
-- Generated: 2026-04-08 06:17:35 UTC
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
-- ============================================

-- Install and load httpfs for remote access
INSTALL httpfs;
LOAD httpfs;

-- Manifest table (index of all files)
CREATE TABLE IF NOT EXISTS manifest AS
SELECT * FROM read_parquet('https://archive.org/download/causaganha-catalog/manifest.parquet');

-- Backfill needed (what's missing)
CREATE TABLE IF NOT EXISTS backfill_needed AS
SELECT * FROM read_parquet('https://archive.org/download/causaganha-catalog/backfill-needed.parquet');

-- ============================================
-- REMOTE VIEWS (query directly from IA)
-- ============================================

-- advogado_nomes: 19 files
CREATE OR REPLACE VIEW advogado_nomes AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-03/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-23/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-22/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-29/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-15/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-27/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-09/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-16/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-19/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-05/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-02/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-10/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-20/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-21/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-28/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-26/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-13/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-16/advogado_nomes.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-23/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-21/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-19/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-28/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-27/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-02/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-20/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-03/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-10/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-05/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-26/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-16/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-30/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-09/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-22/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-01-15/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-16/advogado_nomes.parquet',
    'https://archive.org/download/djen-2026-02-13/advogado_nomes.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- advogados: 19 files
CREATE OR REPLACE VIEW advogados AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/advogados.parquet',
    'https://archive.org/download/djen-2026-02-03/advogados.parquet',
    'https://archive.org/download/djen-2026-01-23/advogados.parquet',
    'https://archive.org/download/djen-2026-01-22/advogados.parquet',
    'https://archive.org/download/djen-2026-01-29/advogados.parquet',
    'https://archive.org/download/djen-2026-01-15/advogados.parquet',
    'https://archive.org/download/djen-2026-01-27/advogados.parquet',
    'https://archive.org/download/djen-2026-02-09/advogados.parquet',
    'https://archive.org/download/djen-2026-01-16/advogados.parquet',
    'https://archive.org/download/djen-2026-01-19/advogados.parquet',
    'https://archive.org/download/djen-2026-02-05/advogados.parquet',
    'https://archive.org/download/djen-2026-02-02/advogados.parquet',
    'https://archive.org/download/djen-2026-02-10/advogados.parquet',
    'https://archive.org/download/djen-2026-01-20/advogados.parquet',
    'https://archive.org/download/djen-2026-01-21/advogados.parquet',
    'https://archive.org/download/djen-2026-01-28/advogados.parquet',
    'https://archive.org/download/djen-2026-01-26/advogados.parquet',
    'https://archive.org/download/djen-2026-02-13/advogados.parquet',
    'https://archive.org/download/djen-2026-02-16/advogados.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/advogados.parquet',
    'https://archive.org/download/djen-2026-01-23/advogados.parquet',
    'https://archive.org/download/djen-2026-01-21/advogados.parquet',
    'https://archive.org/download/djen-2026-01-19/advogados.parquet',
    'https://archive.org/download/djen-2026-01-28/advogados.parquet',
    'https://archive.org/download/djen-2026-01-27/advogados.parquet',
    'https://archive.org/download/djen-2026-02-02/advogados.parquet',
    'https://archive.org/download/djen-2026-01-20/advogados.parquet',
    'https://archive.org/download/djen-2026-02-03/advogados.parquet',
    'https://archive.org/download/djen-2026-02-10/advogados.parquet',
    'https://archive.org/download/djen-2026-02-05/advogados.parquet',
    'https://archive.org/download/djen-2026-01-26/advogados.parquet',
    'https://archive.org/download/djen-2026-01-16/advogados.parquet',
    'https://archive.org/download/djen-2026-01-30/advogados.parquet',
    'https://archive.org/download/djen-2026-02-09/advogados.parquet',
    'https://archive.org/download/djen-2026-01-22/advogados.parquet',
    'https://archive.org/download/djen-2026-01-15/advogados.parquet',
    'https://archive.org/download/djen-2026-02-16/advogados.parquet',
    'https://archive.org/download/djen-2026-02-13/advogados.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- comunicacao_advogados: 19 files
CREATE OR REPLACE VIEW comunicacao_advogados AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-03/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-23/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-22/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-29/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-15/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-27/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-09/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-16/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-19/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-05/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-02/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-10/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-20/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-21/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-28/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-26/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-13/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-16/comunicacao_advogados.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-23/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-21/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-19/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-28/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-27/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-02/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-20/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-03/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-10/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-05/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-26/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-16/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-30/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-09/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-22/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-01-15/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-16/comunicacao_advogados.parquet',
    'https://archive.org/download/djen-2026-02-13/comunicacao_advogados.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- comunicacoes: 19 files
CREATE OR REPLACE VIEW comunicacoes AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-03/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-23/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-22/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-29/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-15/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-27/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-09/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-16/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-19/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-05/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-02/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-10/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-20/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-21/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-28/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-26/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-13/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-16/comunicacoes.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-23/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-21/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-19/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-28/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-27/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-02/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-20/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-03/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-10/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-05/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-26/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-16/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-30/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-09/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-22/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-01-15/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-16/comunicacoes.parquet',
    'https://archive.org/download/djen-2026-02-13/comunicacoes.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- destinatarios: 19 files
CREATE OR REPLACE VIEW destinatarios AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-03/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-23/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-22/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-29/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-15/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-27/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-09/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-16/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-19/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-05/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-02/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-10/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-20/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-21/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-28/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-26/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-13/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-16/destinatarios.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-23/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-21/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-19/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-28/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-27/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-02/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-20/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-03/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-10/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-05/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-26/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-16/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-30/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-09/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-22/destinatarios.parquet',
    'https://archive.org/download/djen-2026-01-15/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-16/destinatarios.parquet',
    'https://archive.org/download/djen-2026-02-13/destinatarios.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- partes: 20 files
CREATE OR REPLACE VIEW partes AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/partes.parquet',
    'https://archive.org/download/djen-2026-02-03/partes.parquet',
    'https://archive.org/download/djen-2026-01-23/partes.parquet',
    'https://archive.org/download/djen-2026-01-22/partes.parquet',
    'https://archive.org/download/djen-2026-01-29/partes.parquet',
    'https://archive.org/download/djen-2026-01-15/partes.parquet',
    'https://archive.org/download/djen-2026-01-27/partes.parquet',
    'https://archive.org/download/djen-2026-02-09/partes.parquet',
    'https://archive.org/download/djen-2026-01-16/partes.parquet',
    'https://archive.org/download/djen-2026-01-19/partes.parquet',
    'https://archive.org/download/djen-2026-02-06/partes.parquet',
    'https://archive.org/download/djen-2026-02-05/partes.parquet',
    'https://archive.org/download/djen-2026-02-02/partes.parquet',
    'https://archive.org/download/djen-2026-02-10/partes.parquet',
    'https://archive.org/download/djen-2026-01-20/partes.parquet',
    'https://archive.org/download/djen-2026-01-21/partes.parquet',
    'https://archive.org/download/djen-2026-01-28/partes.parquet',
    'https://archive.org/download/djen-2026-01-26/partes.parquet',
    'https://archive.org/download/djen-2026-02-13/partes.parquet',
    'https://archive.org/download/djen-2026-02-16/partes.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/partes.parquet',
    'https://archive.org/download/djen-2026-01-23/partes.parquet',
    'https://archive.org/download/djen-2026-01-21/partes.parquet',
    'https://archive.org/download/djen-2026-01-19/partes.parquet',
    'https://archive.org/download/djen-2026-01-28/partes.parquet',
    'https://archive.org/download/djen-2026-01-27/partes.parquet',
    'https://archive.org/download/djen-2026-02-02/partes.parquet',
    'https://archive.org/download/djen-2026-01-20/partes.parquet',
    'https://archive.org/download/djen-2026-02-03/partes.parquet',
    'https://archive.org/download/djen-2026-02-06/partes.parquet',
    'https://archive.org/download/djen-2026-02-10/partes.parquet',
    'https://archive.org/download/djen-2026-02-05/partes.parquet',
    'https://archive.org/download/djen-2026-01-26/partes.parquet',
    'https://archive.org/download/djen-2026-01-16/partes.parquet',
    'https://archive.org/download/djen-2026-01-30/partes.parquet',
    'https://archive.org/download/djen-2026-02-09/partes.parquet',
    'https://archive.org/download/djen-2026-01-22/partes.parquet',
    'https://archive.org/download/djen-2026-01-15/partes.parquet',
    'https://archive.org/download/djen-2026-02-16/partes.parquet',
    'https://archive.org/download/djen-2026-02-13/partes.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- processos: 19 files
CREATE OR REPLACE VIEW processos AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/processos.parquet',
    'https://archive.org/download/djen-2026-02-03/processos.parquet',
    'https://archive.org/download/djen-2026-01-23/processos.parquet',
    'https://archive.org/download/djen-2026-01-22/processos.parquet',
    'https://archive.org/download/djen-2026-01-29/processos.parquet',
    'https://archive.org/download/djen-2026-01-15/processos.parquet',
    'https://archive.org/download/djen-2026-01-27/processos.parquet',
    'https://archive.org/download/djen-2026-02-09/processos.parquet',
    'https://archive.org/download/djen-2026-01-16/processos.parquet',
    'https://archive.org/download/djen-2026-01-19/processos.parquet',
    'https://archive.org/download/djen-2026-02-05/processos.parquet',
    'https://archive.org/download/djen-2026-02-02/processos.parquet',
    'https://archive.org/download/djen-2026-02-10/processos.parquet',
    'https://archive.org/download/djen-2026-01-20/processos.parquet',
    'https://archive.org/download/djen-2026-01-21/processos.parquet',
    'https://archive.org/download/djen-2026-01-28/processos.parquet',
    'https://archive.org/download/djen-2026-01-26/processos.parquet',
    'https://archive.org/download/djen-2026-02-13/processos.parquet',
    'https://archive.org/download/djen-2026-02-16/processos.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/processos.parquet',
    'https://archive.org/download/djen-2026-01-23/processos.parquet',
    'https://archive.org/download/djen-2026-01-21/processos.parquet',
    'https://archive.org/download/djen-2026-01-19/processos.parquet',
    'https://archive.org/download/djen-2026-01-28/processos.parquet',
    'https://archive.org/download/djen-2026-01-27/processos.parquet',
    'https://archive.org/download/djen-2026-02-02/processos.parquet',
    'https://archive.org/download/djen-2026-01-20/processos.parquet',
    'https://archive.org/download/djen-2026-02-03/processos.parquet',
    'https://archive.org/download/djen-2026-02-10/processos.parquet',
    'https://archive.org/download/djen-2026-02-05/processos.parquet',
    'https://archive.org/download/djen-2026-01-26/processos.parquet',
    'https://archive.org/download/djen-2026-01-16/processos.parquet',
    'https://archive.org/download/djen-2026-01-30/processos.parquet',
    'https://archive.org/download/djen-2026-02-09/processos.parquet',
    'https://archive.org/download/djen-2026-01-22/processos.parquet',
    'https://archive.org/download/djen-2026-01-15/processos.parquet',
    'https://archive.org/download/djen-2026-02-16/processos.parquet',
    'https://archive.org/download/djen-2026-02-13/processos.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- representacoes: 19 files
CREATE OR REPLACE VIEW representacoes AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-03/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-23/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-22/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-29/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-15/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-27/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-09/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-16/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-19/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-05/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-02/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-10/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-20/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-21/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-28/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-26/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-13/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-16/representacoes.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-23/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-21/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-19/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-28/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-27/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-02/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-20/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-03/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-10/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-05/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-26/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-16/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-30/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-09/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-22/representacoes.parquet',
    'https://archive.org/download/djen-2026-01-15/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-16/representacoes.parquet',
    'https://archive.org/download/djen-2026-02-13/representacoes.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- textos: 19 files
CREATE OR REPLACE VIEW textos AS
SELECT * FROM read_parquet([
<<<<<<< HEAD
    'https://archive.org/download/djen-2026-01-30/textos.parquet',
    'https://archive.org/download/djen-2026-02-03/textos.parquet',
    'https://archive.org/download/djen-2026-01-23/textos.parquet',
    'https://archive.org/download/djen-2026-01-22/textos.parquet',
    'https://archive.org/download/djen-2026-01-29/textos.parquet',
    'https://archive.org/download/djen-2026-01-15/textos.parquet',
    'https://archive.org/download/djen-2026-01-27/textos.parquet',
    'https://archive.org/download/djen-2026-02-09/textos.parquet',
    'https://archive.org/download/djen-2026-01-16/textos.parquet',
    'https://archive.org/download/djen-2026-01-19/textos.parquet',
    'https://archive.org/download/djen-2026-02-05/textos.parquet',
    'https://archive.org/download/djen-2026-02-02/textos.parquet',
    'https://archive.org/download/djen-2026-02-10/textos.parquet',
    'https://archive.org/download/djen-2026-01-20/textos.parquet',
    'https://archive.org/download/djen-2026-01-21/textos.parquet',
    'https://archive.org/download/djen-2026-01-28/textos.parquet',
    'https://archive.org/download/djen-2026-01-26/textos.parquet',
    'https://archive.org/download/djen-2026-02-13/textos.parquet',
    'https://archive.org/download/djen-2026-02-16/textos.parquet'
=======
    'https://archive.org/download/djen-2026-01-29/textos.parquet',
    'https://archive.org/download/djen-2026-01-23/textos.parquet',
    'https://archive.org/download/djen-2026-01-21/textos.parquet',
    'https://archive.org/download/djen-2026-01-19/textos.parquet',
    'https://archive.org/download/djen-2026-01-28/textos.parquet',
    'https://archive.org/download/djen-2026-01-27/textos.parquet',
    'https://archive.org/download/djen-2026-02-02/textos.parquet',
    'https://archive.org/download/djen-2026-01-20/textos.parquet',
    'https://archive.org/download/djen-2026-02-03/textos.parquet',
    'https://archive.org/download/djen-2026-02-10/textos.parquet',
    'https://archive.org/download/djen-2026-02-05/textos.parquet',
    'https://archive.org/download/djen-2026-01-26/textos.parquet',
    'https://archive.org/download/djen-2026-01-16/textos.parquet',
    'https://archive.org/download/djen-2026-01-30/textos.parquet',
    'https://archive.org/download/djen-2026-02-09/textos.parquet',
    'https://archive.org/download/djen-2026-01-22/textos.parquet',
    'https://archive.org/download/djen-2026-01-15/textos.parquet',
    'https://archive.org/download/djen-2026-02-16/textos.parquet',
    'https://archive.org/download/djen-2026-02-13/textos.parquet'
>>>>>>> 7bcb6ff (feat: implement omission cost visualization widget (#253))
]);

-- ============================================
-- HELPER VIEWS
-- ============================================

-- Collection status by date
CREATE OR REPLACE VIEW collection_status AS
SELECT
    date,
    COUNT(DISTINCT tribunal) as tribunals_collected,
    SUM(CASE WHEN file_type = 'zip' THEN 1 ELSE 0 END) as zip_files,
    SUM(CASE WHEN file_type = 'parquet' THEN 1 ELSE 0 END) as parquet_files
FROM manifest
GROUP BY date
ORDER BY date DESC;

-- Backfill progress
CREATE OR REPLACE VIEW backfill_progress AS
SELECT
    (SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') as collected,
    (SELECT COUNT(*) FROM backfill_needed) as pending,
    ROUND(100.0 * (SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') /
        ((SELECT COUNT(DISTINCT date || tribunal) FROM manifest WHERE file_type = 'zip') +
         (SELECT COUNT(*) FROM backfill_needed)), 2) as percent_complete;
