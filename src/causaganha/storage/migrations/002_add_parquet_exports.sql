-- Migration to add Parquet export tracking to Internet Archive
-- Run this to enable tracking of daily Parquet exports for data lake

-- Step 1: Create parquet_exports table
CREATE SEQUENCE IF NOT EXISTS parquet_exports_id_seq START 1;

CREATE TABLE IF NOT EXISTS parquet_exports (
    id INTEGER PRIMARY KEY DEFAULT nextval('parquet_exports_id_seq'),
    tribunal VARCHAR NOT NULL,
    partition_date DATE NOT NULL,
    ia_item_id VARCHAR NOT NULL,
    ia_url VARCHAR NOT NULL,
    parquet_filename VARCHAR NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    file_size_mb FLOAT NOT NULL CHECK (file_size_mb >= 0),
    uploaded_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('pending', 'uploading', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tribunal, partition_date)
);

-- Step 2: Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_parquet_exports_date
    ON parquet_exports(partition_date DESC);

CREATE INDEX IF NOT EXISTS idx_parquet_exports_tribunal
    ON parquet_exports(tribunal, partition_date DESC);

CREATE INDEX IF NOT EXISTS idx_parquet_exports_status
    ON parquet_exports(status, partition_date DESC);

-- Step 3: Create view for export statistics
CREATE OR REPLACE VIEW export_statistics AS
SELECT
    partition_date,
    COUNT(*) as total_exports,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_exports,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_exports,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_exports,
    ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct,
    SUM(row_count) as total_rows_exported,
    SUM(file_size_mb) as total_size_mb,
    MIN(uploaded_at) as first_upload,
    MAX(uploaded_at) as last_upload
FROM parquet_exports
GROUP BY partition_date
ORDER BY partition_date DESC;

-- Step 4: Create view for problematic tribunals
CREATE OR REPLACE VIEW problematic_tribunals AS
SELECT
    tribunal,
    COUNT(*) as total_exports,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 2) as failure_rate_pct,
    MAX(partition_date) as last_export_date,
    -- Get most recent error message
    (SELECT error_message FROM parquet_exports pe2
     WHERE pe2.tribunal = parquet_exports.tribunal
     AND pe2.status = 'failed'
     ORDER BY pe2.partition_date DESC LIMIT 1) as last_error
FROM parquet_exports
GROUP BY tribunal
HAVING SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) > 0
ORDER BY failure_rate_pct DESC;

-- Step 5: Create view for storage tracking
CREATE OR REPLACE VIEW storage_growth AS
SELECT
    DATE_TRUNC('month', partition_date) as month,
    COUNT(*) as files_created,
    SUM(row_count) as total_decisions,
    SUM(file_size_mb) as total_size_mb,
    ROUND(SUM(file_size_mb) / 1024.0, 2) as total_size_gb,
    ROUND(AVG(file_size_mb), 2) as avg_file_size_mb
FROM parquet_exports
WHERE status = 'completed'
GROUP BY DATE_TRUNC('month', partition_date)
ORDER BY month DESC;

-- Step 6: Add comment documentation
COMMENT ON TABLE parquet_exports IS 'Tracks Parquet file exports to Internet Archive data lake';
COMMENT ON COLUMN parquet_exports.tribunal IS 'Tribunal code (e.g., TJRO, TJSP)';
COMMENT ON COLUMN parquet_exports.partition_date IS 'Date partition (YYYY-MM-DD) for the exported data';
COMMENT ON COLUMN parquet_exports.ia_item_id IS 'Internet Archive item identifier (e.g., causaganha-2025-01-15-TJRO)';
COMMENT ON COLUMN parquet_exports.ia_url IS 'Full URL to Internet Archive item';
COMMENT ON COLUMN parquet_exports.parquet_filename IS 'Filename: causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet';
COMMENT ON COLUMN parquet_exports.row_count IS 'Number of intimation rows exported in this partition';
COMMENT ON COLUMN parquet_exports.file_size_mb IS 'Parquet file size in megabytes (compressed)';
COMMENT ON COLUMN parquet_exports.uploaded_at IS 'Timestamp when upload to IA completed';
COMMENT ON COLUMN parquet_exports.status IS 'Export status: pending, uploading, completed, failed';
COMMENT ON COLUMN parquet_exports.error_message IS 'Error details if status is failed';
