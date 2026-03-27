-- Archival log to track cold storage tarballs
CREATE TABLE IF NOT EXISTS archival_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tribunal VARCHAR(10) NOT NULL,
    archive_year INTEGER NOT NULL,
    archive_month INTEGER NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'archived', -- 'archived', 'restoring', 'restored'
    file_count INTEGER,
    total_size_mb FLOAT,
    archived_at TIMESTAMP DEFAULT NOW(),
    restored_at TIMESTAMP,
    UNIQUE (tribunal, archive_year, archive_month)
);

CREATE INDEX IF NOT EXISTS idx_archival_log_date
    ON archival_log(archive_year DESC, archive_month DESC);

-- Audit log for LGPD compliance tracking
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_identifier VARCHAR(255) NOT NULL, -- IP, email, or token ID
    action_type VARCHAR(50) NOT NULL,      -- 'access_dashboard', 'export_data', 'api_query'
    resource_accessed TEXT NOT NULL,       -- e.g., 'Tribunal TJSP, Filters: Date Range'
    accessed_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_date
    ON audit_log(accessed_at DESC);
