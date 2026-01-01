"""Database schema definitions for V2."""

import ibis


def apply_schema(con: ibis.BaseBackend) -> None:
    """Create all tables if they don't exist.

    Using raw SQL for now to ensure proper types and constraints
    that might be tricky with Ibis create_table API.
    """
    # Monitored Courts
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS monitored_courts (
            sigla_tribunal VARCHAR(10) PRIMARY KEY,
            name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            last_sync_date DATE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Intimations (Metadata)
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS intimations (
            id BIGINT PRIMARY KEY,
            numero_processo VARCHAR(25) NOT NULL,
            numeroprocessocommascara VARCHAR(30),
            data_disponibilizacao DATE NOT NULL,
            sigla_tribunal VARCHAR(10) NOT NULL,
            id_orgao INTEGER,
            tipo_comunicacao VARCHAR(50),
            nome_orgao VARCHAR(255),
            texto TEXT,
            link VARCHAR(500),
            tipo_documento VARCHAR(100),
            nome_classe VARCHAR(255),
            codigo_classe VARCHAR(10),
            hash VARCHAR(100),
            status VARCHAR(1),

            analyzed BOOLEAN DEFAULT FALSE,
            analysis_attempted_at TIMESTAMP,
            analysis_error TEXT,
            analyzed_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Intimation Lawyers
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS intimation_lawyers (
            intimation_id BIGINT REFERENCES intimations(id),
            oab_number VARCHAR(20) NOT NULL,
            oab_state VARCHAR(2) NOT NULL,
            lawyer_name VARCHAR(255),
            polo VARCHAR(1),

            PRIMARY KEY (intimation_id, oab_number, oab_state)
        )
    """)

    # Decision Analysis
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS decision_analysis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            intimation_id BIGINT REFERENCES intimations(id),

            winner_lawyer_oab VARCHAR(20) NOT NULL,
            winner_lawyer_state VARCHAR(2) NOT NULL,
            winner_party_name VARCHAR(255),

            loser_lawyer_oab VARCHAR(20) NOT NULL,
            loser_lawyer_state VARCHAR(2) NOT NULL,
            loser_party_name VARCHAR(255),

            decision_type VARCHAR(50),
            outcome VARCHAR(50),
            judge_name VARCHAR(255),
            decision_reasoning TEXT,

            confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),

            model_used VARCHAR(50),
            model_provider VARCHAR(20),

            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(intimation_id)
        )
    """)

    # Lawyer Ratings
    con.raw_sql("""
        CREATE TABLE IF NOT EXISTS lawyer_ratings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            oab_number VARCHAR(20) NOT NULL,
            oab_state VARCHAR(2) NOT NULL,
            lawyer_name VARCHAR(255),

            mu FLOAT NOT NULL DEFAULT 25.0,
            sigma FLOAT NOT NULL DEFAULT 8.333,

            total_cases INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,

            tribunal VARCHAR(10),
            last_updated TIMESTAMP DEFAULT NOW(),

            UNIQUE(oab_number, oab_state, tribunal)
        )
    """)
