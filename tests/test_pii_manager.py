import pytest
import uuid
from pathlib import Path

# Add src to Python path if running tests directly and conftest isn't picked up the same way
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import CausaGanhaDB, DatabaseManager, run_db_migrations
from src.pii_manager import PiiManager, APPLICATION_NAMESPACE_UUID

# Test PII types
LAWYER_ID_NORMALIZED = "LAWYER_ID_NORMALIZED"
LAWYER_FULL_STRING = "LAWYER_FULL_STRING"
CASE_NUMBER = "CASE_NUMBER"
PARTY_NAME = "PARTY_NAME"


@pytest.fixture
def db_conn(temp_db: Path):
    """Fixture to provide an initialized CausaGanhaDB connection for PiiManager tests."""
    db_manager = DatabaseManager(db_path=temp_db)
    db = CausaGanhaDB(db_manager=db_manager)
    test_migrations_path = db_manager.db_path.parent / "temp_test_migrations"
    test_migrations_path.mkdir(exist_ok=True)
    minimal_schema_sql = """
        CREATE TABLE IF NOT EXISTS pii_decode_map (
            pii_uuid TEXT PRIMARY KEY,
            original_value TEXT NOT NULL,
            value_for_uuid_ref TEXT NOT NULL,
            pii_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    (test_migrations_path / "001_test_schema.sql").write_text(minimal_schema_sql)
    run_db_migrations(db_manager.db_path, migrations_path_override=test_migrations_path) # Ensure migrations are run
    yield db.conn
    db_manager.close()


@pytest.fixture
def pii_manager(db_conn):
    """Fixture to provide a PiiManager instance with a live DB connection."""
    return PiiManager(db_conn)


def test_generate_uuidv5_consistency(pii_manager: PiiManager):
    """Test that UUIDv5 generation is consistent for the same input and PII type."""
    value = "test_string_for_uuid"
    pii_type = "TEST_TYPE_FOR_CONSISTENCY"  # Define a consistent type for this test
    uuid1 = pii_manager._generate_uuidv5(value, pii_type)
    uuid2 = pii_manager._generate_uuidv5(value, pii_type)
    assert uuid1 == uuid2
    assert uuid.UUID(uuid1).version == 5

    # Check against a known UUID generated with the same namespace and name components
    # This requires knowing the namespace UUID used in PiiManager.
    # APPLICATION_NAMESPACE_UUID is imported for this.
    value_to_hash = f"{pii_type}:{value}"  # Reflect the new hashing input
    expected_uuid = str(uuid.uuid5(APPLICATION_NAMESPACE_UUID, value_to_hash))
    assert uuid1 == expected_uuid


def test_uuid_uniqueness_across_pii_types(pii_manager: PiiManager):
    """Test that the same value string generates different UUIDs for different PII types."""
    value = "TestData123"
    pii_type1 = "TYPE_A"
    pii_type2 = "TYPE_B"

    uuid1 = pii_manager.get_or_create_pii_mapping(
        value, pii_type1, normalized_value=value
    )
    uuid2 = pii_manager.get_or_create_pii_mapping(
        value, pii_type2, normalized_value=value
    )

    assert uuid1 != uuid2, (
        "UUIDs should be different for the same value but different PII types."
    )

    retrieved1 = pii_manager.get_original_pii(uuid1)
    retrieved2 = pii_manager.get_original_pii(uuid2)

    assert retrieved1 is not None
    assert retrieved1["original_value"] == value
    assert retrieved1["pii_type"] == pii_type1

    assert retrieved2 is not None
    assert retrieved2["original_value"] == value
    assert retrieved2["pii_type"] == pii_type2


def test_get_or_create_pii_mapping_new(pii_manager: PiiManager):
    """Test creating a new PII mapping."""
    original_value = "João da Silva"
    normalized_value = "joao da silva"
    pii_type = PARTY_NAME

    # First call should create the mapping
    created_uuid = pii_manager.get_or_create_pii_mapping(
        original_value, pii_type, normalized_value
    )
    assert uuid.UUID(created_uuid).version == 5

    # Verify in DB (optional, but good for testing this method thoroughly)
    row = pii_manager.conn.execute(
        "SELECT original_value, value_for_uuid_ref, pii_type FROM pii_decode_map WHERE pii_uuid = ?",
        (created_uuid,),
    ).fetchone()
    assert row is not None
    assert row[0] == original_value
    assert row[1] == normalized_value
    assert row[2] == pii_type


def test_get_or_create_pii_mapping_existing(pii_manager: PiiManager):
    """Test retrieving an existing PII mapping."""
    original_value = "Maria Oliveira"
    normalized_value = "maria oliveira"
    pii_type = PARTY_NAME

    uuid1 = pii_manager.get_or_create_pii_mapping(
        original_value, pii_type, normalized_value
    )
    uuid2 = pii_manager.get_or_create_pii_mapping(
        original_value, pii_type, normalized_value
    )  # Same inputs
    assert uuid1 == uuid2

    # Test with slightly different original_value but same normalized_value
    uuid3 = pii_manager.get_or_create_pii_mapping(
        "Dra. Maria Oliveira", pii_type, normalized_value
    )
    assert (
        uuid1 == uuid3
    )  # Should map to the same UUID because normalized_value is the key for generation


def test_get_or_create_pii_mapping_no_normalization(pii_manager: PiiManager):
    """Test mapping when no explicit normalized value is provided."""
    original_value = "0012345-67.2023.8.22.0001"
    pii_type = CASE_NUMBER

    # If normalized_value is None, original_value is used for UUID generation and as value_for_uuid_ref
    created_uuid = pii_manager.get_or_create_pii_mapping(
        original_value, pii_type, normalized_value=None
    )

    row = pii_manager.conn.execute(
        "SELECT original_value, value_for_uuid_ref, pii_type FROM pii_decode_map WHERE pii_uuid = ?",
        (created_uuid,),
    ).fetchone()
    assert row is not None
    assert row[0] == original_value
    assert row[1] == original_value  # value_for_uuid_ref should be original_value
    assert row[2] == pii_type


def test_get_original_pii_existing(pii_manager: PiiManager):
    """Test decoding an existing PII UUID."""
    normalized_value = (
        "fulano ciclano"  # This is what the UUID is based on for LAWYER_ID_NORMALIZED
    )
    pii_type = LAWYER_ID_NORMALIZED

    # Create the mapping: original_value here is the normalized form for this PII type
    # because that's what we want to decode back to for this type.
    pii_uuid = pii_manager.get_or_create_pii_mapping(
        normalized_value, pii_type, normalized_value
    )

    decoded_info = pii_manager.get_original_pii(pii_uuid, requester_info="TEST_SUITE")
    assert decoded_info is not None
    assert (
        decoded_info["original_value"] == normalized_value
    )  # We stored normalized_value as original_value for this type
    assert decoded_info["pii_type"] == pii_type


def test_get_original_pii_non_existent(pii_manager: PiiManager):
    """Test decoding a non-existent PII UUID."""
    non_existent_uuid = str(uuid.uuid4())  # Random UUID
    decoded_info = pii_manager.get_original_pii(
        non_existent_uuid, requester_info="TEST_SUITE"
    )
    assert decoded_info is None


def test_get_or_create_pii_mapping_empty_values(pii_manager: PiiManager):
    """Test behavior with empty or whitespace strings."""
    with pytest.raises(ValueError, match="Original value cannot be empty"):
        pii_manager.get_or_create_pii_mapping("", "TEST_TYPE", "")

    with pytest.raises(ValueError, match="Value for UUID generation cannot be empty"):
        pii_manager.get_or_create_pii_mapping("Some Original", "TEST_TYPE", "  ")

    # This case should NOT raise an error, as "Some Original" is a valid value_for_uuid
    # If normalized_value is None, original_value ("Some Original") is used.
    try:
        pii_manager.get_or_create_pii_mapping("Some Original", "TEST_TYPE", None)
    except ValueError as e:
        if "Value for UUID generation cannot be empty" in str(e):
            pytest.fail(
                "ValueError for non-empty original_value when normalized_value is None was incorrectly raised."
            )
        else:
            raise  # Re-raise other ValueErrors if any

    # This case SHOULD raise an error as original_value itself becomes an empty value_for_uuid after strip()
    with pytest.raises(
        ValueError, match="Value for UUID generation cannot be empty or whitespace"
    ):
        pii_manager.get_or_create_pii_mapping("   ", "TEST_TYPE", None)


# Placeholder tests for text replacement helpers - would need more robust versions of these helpers
# For now, they are very basic in pii_manager.py


def test_replace_pii_in_text(pii_manager: PiiManager):
    original_text = "Nome Teste"
    pii_type = PARTY_NAME

    # Simple normalization for testing (lowercase)
    def simple_norm(text):
        return text.lower()

    uuid_val = pii_manager.replace_pii_in_text(original_text, pii_type, simple_norm)
    assert uuid_val is not None

    decoded = pii_manager.get_original_pii(uuid_val)
    assert decoded["original_value"] == original_text  # Stores original

    # Test that the UUID was based on normalized value
    expected_uuid_for_normalized = pii_manager._generate_uuidv5(
        simple_norm(original_text), pii_type
    )  # Pass pii_type
    assert uuid_val == expected_uuid_for_normalized

    assert pii_manager.replace_pii_in_text(None, pii_type) is None
    assert (
        pii_manager.replace_pii_in_text("  ", pii_type) == "  "
    )  # Current behavior for whitespace only


def test_replace_pii_in_list(pii_manager: PiiManager):
    original_list = ["Nome A", "Nome B", None, "  "]
    pii_type = PARTY_NAME
    uuid_list = pii_manager.replace_pii_in_list(
        original_list, pii_type, lambda x: x.lower() if x else None
    )

    assert (
        len(uuid_list) == 3
    )  # None is skipped, "  " is kept as is by replace_pii_in_text
    assert uuid.UUID(uuid_list[0])  # Check if valid UUIDs
    assert uuid.UUID(uuid_list[1])
    assert uuid_list[2] == "  "  # Whitespace string passes through

    assert pii_manager.replace_pii_in_list(None, pii_type) is None


# More tests could be added for replace_pii_in_dict_keys and replace_pii_in_json_string
# if those helper functions in PiiManager were made more robust.
# The current replace_pii_in_json_string is a very basic placeholder.
