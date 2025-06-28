import duckdb
from src.pii_manager import PiiManager
from src.anonymization_hooks import anonymize_metadata


def test_anonymize_metadata_replaces_fields():
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE pii_decode_map (
            pii_uuid TEXT PRIMARY KEY,
            original_value TEXT NOT NULL,
            value_for_uuid_ref TEXT NOT NULL,
            pii_type TEXT NOT NULL
        )
        """
    )
    pm = PiiManager(conn)
    metadata = {"creator": "Joao Silva", "title": "Processo 123", "subject": "test"}
    sanitized = anonymize_metadata(metadata, pm)
    assert sanitized["creator"] != "Joao Silva"
    assert sanitized["title"] != "Processo 123"
    assert sanitized["subject"] == "test"
