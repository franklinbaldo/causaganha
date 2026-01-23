-- Migration to add RAG analysis support to decision_analysis table
-- Run this to enable RAG-based analysis alongside LLM analysis

-- Step 1: Make lawyer OAB fields nullable (RAG doesn't extract lawyer info)
ALTER TABLE decision_analysis ALTER COLUMN winner_lawyer_oab DROP NOT NULL;
ALTER TABLE decision_analysis ALTER COLUMN winner_lawyer_state DROP NOT NULL;
ALTER TABLE decision_analysis ALTER COLUMN loser_lawyer_oab DROP NOT NULL;
ALTER TABLE decision_analysis ALTER COLUMN loser_lawyer_state DROP NOT NULL;

-- Step 2: Add analysis method tracking
ALTER TABLE decision_analysis ADD COLUMN IF NOT EXISTS analysis_method VARCHAR(30) DEFAULT 'llm';

-- Step 3: Add RAG-specific fields
ALTER TABLE decision_analysis ADD COLUMN IF NOT EXISTS rag_confidence FLOAT CHECK (rag_confidence IS NULL OR (rag_confidence BETWEEN 0 AND 1));
ALTER TABLE decision_analysis ADD COLUMN IF NOT EXISTS rag_votes_json VARCHAR;

-- Step 4: Create index for analysis method filtering
CREATE INDEX IF NOT EXISTS idx_decision_analysis_method
    ON decision_analysis(analysis_method, created_at DESC);

-- Step 5: Create view for RAG vs LLM comparison
CREATE OR REPLACE VIEW analysis_method_stats AS
SELECT
    analysis_method,
    COUNT(*) as total_analyses,
    AVG(confidence_score) as avg_confidence,
    AVG(rag_confidence) as avg_rag_confidence,
    SUM(CASE WHEN analysis_method = 'rag' THEN 1 ELSE 0 END) as rag_count,
    SUM(CASE WHEN analysis_method = 'hybrid' THEN 1 ELSE 0 END) as hybrid_count,
    SUM(CASE WHEN analysis_method = 'llm' THEN 1 ELSE 0 END) as llm_count,
    -- Cost estimation (assuming $0.000008 for RAG, $0.000420 for LLM/hybrid)
    SUM(CASE
        WHEN analysis_method = 'rag' THEN 0.000008
        WHEN analysis_method IN ('llm', 'hybrid') THEN 0.000420
        ELSE 0
    END) as estimated_total_cost
FROM decision_analysis
GROUP BY analysis_method;
