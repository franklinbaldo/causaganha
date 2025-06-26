-- Migration 002: Archived Databases Table
-- Adds table to track Internet Archive database snapshots
-- Date: 2025-06-26

-- Tabela archived_databases - Internet Archive database snapshots tracking
CREATE TABLE IF NOT EXISTS archived_databases (
    id INTEGER PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    archive_type VARCHAR(20) NOT NULL CHECK (archive_type IN ('weekly', 'monthly', 'quarterly')),
    ia_identifier VARCHAR(100) NOT NULL UNIQUE,
    ia_url TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_hash CHAR(64) NOT NULL,
    total_lawyers INTEGER,
    total_matches INTEGER,
    total_decisions INTEGER,
    upload_status VARCHAR(20) DEFAULT 'pending' CHECK (upload_status IN ('pending', 'uploading', 'completed', 'failed')),
    upload_started_at TIMESTAMP,
    upload_completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_archived_databases_date ON archived_databases(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_archived_databases_type ON archived_databases(archive_type);
CREATE INDEX IF NOT EXISTS idx_archived_databases_status ON archived_databases(upload_status);
CREATE INDEX IF NOT EXISTS idx_archived_databases_ia_id ON archived_databases(ia_identifier);

-- Update estatisticas_gerais view to include archived databases
CREATE OR REPLACE VIEW estatisticas_gerais AS
SELECT 
    (SELECT COUNT(*) FROM ratings) as total_advogados,
    (SELECT COUNT(*) FROM ratings WHERE total_partidas > 0) as advogados_ativos,
    (SELECT AVG(mu) FROM ratings WHERE total_partidas > 0) as mu_medio,
    (SELECT AVG(sigma) FROM ratings WHERE total_partidas > 0) as sigma_medio,
    (SELECT MAX(total_partidas) FROM ratings) as max_partidas,
    (SELECT COUNT(*) FROM partidas) as total_partidas,
    (SELECT COUNT(*) FROM pdf_metadata) as total_pdfs,
    (SELECT COUNT(*) FROM pdf_metadata WHERE upload_status = 'uploaded') as pdfs_arquivados,
    (SELECT COUNT(*) FROM decisoes) as total_decisoes,
    (SELECT COUNT(*) FROM decisoes WHERE validation_status = 'valid') as decisoes_validas,
    (SELECT COUNT(*) FROM json_files) as total_json_files,
    (SELECT COUNT(*) FROM json_files WHERE processing_status = 'completed') as json_files_processados,
    (SELECT COUNT(*) FROM pdfs) as total_pdfs_ia,
    (SELECT COUNT(*) FROM pdfs WHERE upload_status = 'uploaded') as pdfs_ia_uploaded,
    (SELECT COUNT(*) FROM archived_databases) as total_database_archives,
    (SELECT COUNT(*) FROM archived_databases WHERE upload_status = 'completed') as database_archives_completed,
    (SELECT MAX(snapshot_date) FROM archived_databases WHERE upload_status = 'completed') as latest_archive_date;

-- View for archive status and history
CREATE OR REPLACE VIEW archive_status AS
SELECT 
    snapshot_date,
    archive_type,
    ia_identifier,
    ia_url,
    ROUND(file_size_bytes / 1024.0 / 1024.0, 2) as file_size_mb,
    total_lawyers,
    total_matches,
    total_decisions,
    upload_status,
    upload_completed_at,
    CASE 
        WHEN upload_completed_at IS NOT NULL THEN 
            ROUND(EXTRACT('epoch' FROM upload_completed_at - upload_started_at) / 60.0, 1)
        ELSE NULL 
    END as upload_duration_minutes,
    created_at
FROM archived_databases
ORDER BY snapshot_date DESC;