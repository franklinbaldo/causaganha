-- Migration 003: Queue System for Pipeline Processing
-- This migration adds queue tables for robust, fault-tolerant PDF processing

-- PDF Discovery Queue
-- Stores URLs discovered from TJRO website for download
CREATE TABLE IF NOT EXISTS pdf_discovery_queue (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    date TEXT NOT NULL,  -- YYYY-MM-DD format
    number TEXT,         -- e.g., "249", "249S" 
    year INTEGER NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,  -- Higher numbers = higher priority
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    metadata JSON,       -- Store original TJRO API response
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PDF Archive Queue
-- Tracks PDFs that need to be archived to Internet Archive
CREATE TABLE IF NOT EXISTS pdf_archive_queue (
    id INTEGER PRIMARY KEY,
    pdf_id INTEGER NOT NULL,
    local_path TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    ia_url TEXT,         -- Internet Archive URL after successful upload
    ia_item_id TEXT,     -- Internet Archive item identifier
    upload_size_bytes INTEGER,
    upload_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

-- PDF Extraction Queue  
-- Tracks PDFs that need content extraction with Gemini
CREATE TABLE IF NOT EXISTS pdf_extraction_queue (
    id INTEGER PRIMARY KEY,
    pdf_id INTEGER NOT NULL,
    local_path TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    extraction_result JSON,  -- Store Gemini response
    decisions_found INTEGER DEFAULT 0,
    processing_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

-- Rating Processing Queue
-- Tracks PDFs that need TrueSkill rating updates
CREATE TABLE IF NOT EXISTS rating_processing_queue (
    id INTEGER PRIMARY KEY,
    pdf_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    decisions_processed INTEGER DEFAULT 0,
    ratings_updated INTEGER DEFAULT 0,
    matches_created INTEGER DEFAULT 0,
    processing_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

-- Queue Processing Log
-- Audit trail for queue processing activities
CREATE TABLE IF NOT EXISTS queue_processing_log (
    id INTEGER PRIMARY KEY,
    queue_type TEXT NOT NULL,  -- 'discovery', 'archive', 'extraction', 'ratings'
    queue_item_id INTEGER NOT NULL,
    action TEXT NOT NULL,      -- 'started', 'completed', 'failed', 'retried'
    message TEXT,
    processing_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhance existing pdfs table with queue tracking
ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS discovery_queue_id INTEGER;
ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER;
ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS download_duration_ms INTEGER;
ALTER TABLE pdfs ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending';

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_discovery_queue_status_priority ON pdf_discovery_queue(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_discovery_queue_date ON pdf_discovery_queue(date);
CREATE INDEX IF NOT EXISTS idx_discovery_queue_year ON pdf_discovery_queue(year);
CREATE INDEX IF NOT EXISTS idx_discovery_queue_url ON pdf_discovery_queue(url);

CREATE INDEX IF NOT EXISTS idx_archive_queue_status ON pdf_archive_queue(status);
CREATE INDEX IF NOT EXISTS idx_archive_queue_pdf_id ON pdf_archive_queue(pdf_id);

CREATE INDEX IF NOT EXISTS idx_extraction_queue_status ON pdf_extraction_queue(status);
CREATE INDEX IF NOT EXISTS idx_extraction_queue_pdf_id ON pdf_extraction_queue(pdf_id);

CREATE INDEX IF NOT EXISTS idx_rating_queue_status ON rating_processing_queue(status);
CREATE INDEX IF NOT EXISTS idx_rating_queue_pdf_id ON rating_processing_queue(pdf_id);

CREATE INDEX IF NOT EXISTS idx_processing_log_queue_type ON queue_processing_log(queue_type);
CREATE INDEX IF NOT EXISTS idx_processing_log_created_at ON queue_processing_log(created_at);

-- Note: Triggers removed for DuckDB compatibility
-- Updated timestamps and logging will be handled in application code

-- Views for monitoring and reporting
CREATE VIEW IF NOT EXISTS queue_summary AS
SELECT 
    'discovery' as queue_type,
    COUNT(*) as total_items,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    MIN(created_at) as oldest_item,
    MAX(created_at) as newest_item
FROM pdf_discovery_queue

UNION ALL

SELECT 
    'archive' as queue_type,
    COUNT(*) as total_items,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    MIN(created_at) as oldest_item,
    MAX(created_at) as newest_item
FROM pdf_archive_queue

UNION ALL

SELECT 
    'extraction' as queue_type,
    COUNT(*) as total_items,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    MIN(created_at) as oldest_item,
    MAX(created_at) as newest_item
FROM pdf_extraction_queue

UNION ALL

SELECT 
    'ratings' as queue_type,
    COUNT(*) as total_items,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
    MIN(created_at) as oldest_item,
    MAX(created_at) as newest_item
FROM rating_processing_queue;

-- View for failed items needing attention
CREATE VIEW IF NOT EXISTS failed_queue_items AS
SELECT 
    'discovery' as queue_type,
    id,
    date as item_date,
    url as item_identifier,
    attempts,
    error_message,
    last_attempt,
    created_at
FROM pdf_discovery_queue 
WHERE status = 'failed'

UNION ALL

SELECT 
    'archive' as queue_type,
    aq.id,
    p.date_published as item_date,
    aq.local_path as item_identifier,
    aq.attempts,
    aq.error_message,
    aq.last_attempt,
    aq.created_at
FROM pdf_archive_queue aq
JOIN pdfs p ON aq.pdf_id = p.id
WHERE aq.status = 'failed'

UNION ALL

SELECT 
    'extraction' as queue_type,
    eq.id,
    p.date_published as item_date,
    eq.local_path as item_identifier,
    eq.attempts,
    eq.error_message,
    eq.last_attempt,
    eq.created_at
FROM pdf_extraction_queue eq
JOIN pdfs p ON eq.pdf_id = p.id
WHERE eq.status = 'failed'

UNION ALL

SELECT 
    'ratings' as queue_type,
    rq.id,
    p.date_published as item_date,
    CAST(rq.pdf_id AS TEXT) as item_identifier,
    rq.attempts,
    rq.error_message,
    rq.last_attempt,
    rq.created_at
FROM rating_processing_queue rq
JOIN pdfs p ON rq.pdf_id = p.id
WHERE rq.status = 'failed'

ORDER BY last_attempt DESC;