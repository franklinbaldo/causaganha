# PII Handling and Replacement Strategy

## 1. Overview

This document outlines the strategy implemented in the CausaGanha project for handling Personally Identifiable Information (PII). The primary goal is to enhance data privacy and prepare the system for scenarios where data might be shared or analyzed with reduced exposure of raw PII.

The core of this strategy is the replacement of identified PII fields with deterministic UUIDv5 identifiers. Original PII values are stored securely in a separate mapping table to allow for controlled decoding if necessary.

## 2. PII Identification

The following fields across various database tables have been identified as containing PII and are subject to replacement:

- **`decisoes` table:**
  - `numero_processo`: Case number.
  - `polo_ativo`: JSON array of plaintiff/appellant names.
  - `polo_passivo`: JSON array of defendant/appellee names.
  - `advogados_polo_ativo`: JSON array of lawyer names (potentially including OAB numbers) for the plaintiff/appellant side.
  - `advogados_polo_passivo`: JSON array of lawyer names for the defendant/appellee side.
  - `raw_json_data`: The raw JSON output from Gemini extraction, where PII fields within this structure are also replaced.
- **`partidas` table:**
  - `numero_processo`: Case number (will store the UUID of the case number).
  - `equipe_a_ids`, `equipe_b_ids`: JSON arrays of normalized lawyer ID UUIDs.
  - Keys within JSON fields `ratings_equipe_a_antes`, `ratings_equipe_b_antes`, `ratings_equipe_a_depois`, `ratings_equipe_b_depois`: These keys are normalized lawyer ID UUIDs.
- **`ratings` table:**
  - `advogado_id`: The primary identifier for lawyers, now a UUID representing the normalized lawyer name.

**Types of PII handled:**

- Personal Names (parties involved in cases, lawyers).
- Official Identifiers (case numbers, OAB numbers if present in original lawyer strings).

## 3. Replacement Mechanism

### 3.1 Method: UUIDv5

PII values are replaced with UUIDv5 identifiers. This method was chosen because:

- **Determinism:** UUIDv5 generates a consistent UUID for the same input. In this system, the input for UUID generation is a combination of the `pii_type` and a (potentially normalized) value string (referred to as `value_for_uuid_ref` in the `pii_decode_map` table). This ensures that the same piece of PII (defined by its value and type) always maps to the same UUID. It also guarantees that identical value strings used for different PII types (e.g., a numeric ID that could conceptually be part of a name and also a standalone identifier type) will generate distinct UUIDs, preventing unintended collisions.
- **Decode Map Compatibility:** It provides stable, unique identifiers suitable for use in a decoding map.
- **Uniqueness:** UUIDs have a very low probability of collision.

An application-specific **namespace UUID** is used for all UUIDv5 generation. This namespace should be treated as a configuration secret if the goal is to make it difficult for unauthorized parties to regenerate the PII UUIDs even if they guess the input PII strings.

### 3.2 `pii_decode_map` Table

A dedicated table, `pii_decode_map`, stores the mappings between original PII values and their corresponding UUIDs. This table is essential for any authorized decoding of PII.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS pii_decode_map (
    pii_uuid VARCHAR(36) PRIMARY KEY,    -- The UUIDv5 generated value, serves as the PK
    original_value TEXT NOT NULL,         -- The original PII string (e.g., name, case number)
    value_for_uuid_ref TEXT NOT NULL,     -- The value (often normalized) that, in combination with pii_type, was used to generate pii_uuid
    pii_type VARCHAR(50) NOT NULL,        -- Type of PII (e.g., 'LAWYER_ID_NORMALIZED', 'CASE_NUMBER', 'PARTY_NAME', 'LAWYER_FULL_STRING')
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pii_decode_map_ref_type ON pii_decode_map(value_for_uuid_ref, pii_type);
```

- `pii_uuid`: The UUIDv5 replacement for the PII.
- `original_value`: The actual, original PII string. **This column contains highly sensitive data.**
- `value_for_uuid_ref`: The specific string (often a normalized version of `original_value`) that, in combination with `pii_type`, is used as input to the UUIDv5 generation function. This helps ensure consistent UUID generation for logically equivalent PII that might have different original string representations within the same PII type.
- `pii_type`: A category for the PII (e.g., `LAWYER_ID_NORMALIZED`, `LAWYER_FULL_STRING`, `CASE_NUMBER`, `PARTY_NAME`). This is also part of the input to the UUIDv5 generation function and helps in managing different types of PII and applying specific normalization rules.
- `created_at`: Timestamp of mapping creation.

**Security for `pii_decode_map`:**
This table is critical and must be protected with stringent security measures:

- **Access Control:** Database-level and application-level access controls should restrict read/write access to this table to only highly authorized processes or roles.
- **Encryption at Rest:** The entire database file (which includes this table) should ideally be encrypted at rest using DuckDB's encryption capabilities (e.g., `PRAGMA ENCRYPT`) or filesystem-level encryption. The encryption key must be securely managed.

### 3.3 `PiiManager` (`src/pii_manager.py`)

The `src/pii_manager.py` module contains the `PiiManager` class, which is responsible for:

- Generating UUIDv5 identifiers using the application namespace and input PII values.
- Managing entries in the `pii_decode_map` table via its `get_or_create_pii_mapping` method. This method ensures that a unique PII value (based on its type and reference value) always maps to the same UUID, creating a new mapping if one doesn't exist.
- Providing a controlled way to decode UUIDs back to original PII via the `get_original_pii` method, which includes logging of access attempts.
- Handling different PII types and applying appropriate normalization (e.g., for lawyer names to create a consistent `LAWYER_ID_NORMALIZED`) before UUID generation.

## 4. Integration into the Data Pipeline

PII replacement is integrated into the data processing pipeline as follows:

1.  **Extraction:** The `src/extractor.py` (using Gemini) extracts data, including raw PII, from PDF documents into JSON files. These initial JSON files (typically in `data/json/`) contain original PII.
2.  **Processing & Replacement:** The `src/pipeline.py` script (specifically the `_update_ratings_logic` function) reads these JSON files.
    - For each decision and relevant PII field, it uses `PiiManager` to:
      - Generate/retrieve the UUID for the PII value.
      - Populate/update the `pii_decode_map` table.
    - The PII values in the decision data are then replaced with their corresponding UUIDs.
3.  **Database Storage:** The processed data, now containing UUIDs instead of raw PII in the main analytical fields, is saved to the respective database tables:
    - **`decisoes`**: Stores UUIDs for `numero_processo`. JSON fields like `polo_ativo`, `polo_passivo`, `advogados_polo_ativo`, and `advogados_polo_passivo` store arrays of the relevant PII UUIDs. The `raw_json_data` column also stores a version of the decision data where PII fields have been replaced by UUIDs.
    - **`ratings`**: The `advogado_id` column stores the UUID corresponding to the normalized lawyer name (`LAWYER_ID_NORMALIZED`).
    - **`partidas`**: The `numero_processo` column stores the case number's UUID. The `equipe_a_ids` and `equipe_b_ids` fields store JSON arrays of lawyer rating UUIDs. The keys within the JSON rating history fields (`ratings_equipe_a_antes`, etc.) are also lawyer rating UUIDs.

The original JSON files from extraction are moved to a `data/json_processed/` directory after successful processing. These files still contain raw PII and should be subject to appropriate data retention and security policies.

## 5. Decoding PII (Secure Access)

Decoding PII UUIDs back to their original values is a sensitive operation that should be performed rarely and only by authorized personnel or systems.

- **`scripts/decode_pii_tool.py`:** A command-line tool is provided for this purpose.
  - Usage: `python scripts/decode_pii_tool.py <UUID_TO_DECODE> [--requester <REQUESTER_ID>]`
  - This tool connects to the database, uses `PiiManager.get_original_pii()`, and prints the decoded information.
  - It includes warnings about the sensitivity of the operation.
- **Audit Logging:** All calls to `PiiManager.get_original_pii()` (including those from the decode tool) are logged, including the UUID requested, a requester identifier, and whether the decode was successful. These logs should be monitored as part of security procedures.
- **Operational Security:** Access to run `decode_pii_tool.py` must be strictly controlled via filesystem permissions and user authorization. If the database is encrypted, the decryption key would also be required.

## 6. Data Migration (`scripts/migrate_existing_pii.py`)

For databases that existed before this PII replacement strategy was implemented, a migration script is provided: `scripts/migrate_existing_pii.py`.

- **Purpose:** To scan existing data in `ratings`, `decisoes`, and `partidas` tables, identify raw PII, replace it with UUIDs using `PiiManager`, and update the records in place. It also populates the `pii_decode_map` with mappings from the existing data.
- **Operation:**
  1.  Migrates `ratings` by converting `advogado_id` (normalized names) to UUIDs.
  2.  Migrates `decisoes` by converting `numero_processo` and PII in JSON fields to UUIDs.
  3.  Migrates `partidas` by converting `numero_processo` and lawyer identifiers in team lists and rating dictionaries to UUIDs.
- **CRITICAL WARNING:** This script performs significant in-place modifications to the database. **It is absolutely essential to back up the database thoroughly before running this script.** It should also be tested extensively on a staging or development copy of the database before being run on production data. The script includes a dry-run mode (`--dry-run`) for simulation.

## 7. Impact on Gemini Analysis

- **Input:** Gemini's initial role is to extract information from PDF documents. It receives the original, raw PII as present in these documents. This part of the process remains unchanged.
- **Output:** The JSON files produced by `src/extractor.py` (Gemini's output) contain the extracted raw PII.
- **Downstream Processing:** The PII replacement occurs _after_ Gemini's extraction step, when these JSON files are processed by `src/pipeline.py`.

There is no current requirement for Gemini to perform analysis on already-replaced (UUID-based) PII.

## 8. Future Considerations

- **Enhanced Access Control:** Implement more granular, role-based access controls for the `pii_decode_map` table if the database system and deployment environment allow.
- **Automated Purging:** Define and implement automated purging or stricter retention policies for the intermediate JSON files in `data/json/` and `data/json_processed/` which contain raw PII, if they are not needed long-term.
- **Configuration for Decoding:** The `allow_pii_decoding` flag (mentioned conceptually for `decode_pii_tool.py`) could be implemented as a global switch in `config.toml` for an additional layer of control.
- **Asynchronous PII Replacement:** For very high-throughput systems, the PII replacement step itself could be moved to an asynchronous process, though this adds complexity.
