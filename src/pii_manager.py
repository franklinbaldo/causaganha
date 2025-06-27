import uuid
import json
import logging
from typing import List, Dict, Any, Optional, Union

# This namespace should be unique to this application and kept confidential
# if the goal is to make it harder to regenerate UUIDs without it.
# For development, we can use a fixed one. In production, this might come from a secure config.
APPLICATION_NAMESPACE_UUID = uuid.UUID("0ab3b73f-71ac-45a0-9f08-381f7a3e62df") # Example UUID

logger = logging.getLogger(__name__)

class PiiManager:
    def __init__(self, db_connection):
        """
        Initializes the PiiManager with a database connection.
        Args:
            db_connection: An active DuckDB connection object.
        """
        self.conn = db_connection
        self._ensure_decode_map_table_exists() # Ensure table exists on init (idempotent)

    def _ensure_decode_map_table_exists(self):
        """
        Ensures the pii_decode_map table exists.
        This is more of a safeguard; migrations should handle table creation.
        """
        # This method will be more relevant once migrations are set up.
        # For now, it can be a pass-through or log a message.
        # Actual table creation will be in a migration file.
        logger.debug("PiiManager initialized. Assuming pii_decode_map table handled by migrations.")
        pass

    def _generate_uuidv5(self, value: str) -> str:
        """Generates a UUIDv5 for a given string value."""
        if not isinstance(value, str):
            value = str(value) # Ensure value is a string
        return str(uuid.uuid5(APPLICATION_NAMESPACE_UUID, value))

    def get_or_create_pii_mapping(self, original_value: str, pii_type: str, normalized_value: Optional[str] = None) -> str:
        """
        Gets the UUID for an original PII value, creating a mapping if it doesn't exist.
        The value used for UUID generation is `normalized_value` if provided, otherwise `original_value`.

        Args:
            original_value: The original PII string. This is what's stored for decoding.
            pii_type: The type of PII (e.g., 'LAWYER_NAME', 'CASE_NUMBER').
            normalized_value: An optional normalized version of the PII string. If provided,
                              this is used for UUID generation and for checking existing mappings
                              to ensure different original forms of the same logical PII
                              map to the same UUID.

        Returns:
            The UUID string for the PII.
        """
        if not original_value:
            raise ValueError("Original value cannot be empty for PII mapping.")

        # The value used for generating the UUID and for unique lookup of the PII entity
        value_for_uuid = normalized_value if normalized_value is not None else original_value
        if not value_for_uuid.strip(): # Ensure not just whitespace
             raise ValueError(f"Value for UUID generation cannot be empty or whitespace. Original: '{original_value}', Normalized: '{normalized_value}'")


        generated_uuid = self._generate_uuidv5(value_for_uuid)

        # Check if this UUID already exists
        # Using pii_uuid for lookup is faster due to unique index.
        # We trust that if uuid exists, the original_value and pii_type are consistent
        # OR that the (value_for_uuid, pii_type) combination is what truly defines uniqueness.
        # Let's refine this to check based on (value_for_uuid, pii_type) for robustness.

        # Check if the (value_for_uuid, pii_type) mapping already exists to get its UUID
        # This prevents inserting duplicate (value_for_uuid, pii_type) pairs if somehow
        # original_value differs slightly but normalizes to the same thing.
        query_existing = """
            SELECT pii_uuid FROM pii_decode_map
            WHERE value_for_uuid = ? AND pii_type = ?
        """
        # We need a value_for_uuid column in pii_decode_map
        # Let's adjust the table design slightly:
        # pii_uuid, original_value (for decoding), value_for_uuid (for uniqueness check & UUID gen), pii_type

        # Revised thinking: The UUID is generated from value_for_uuid.
        # So, we first check if this UUID exists. If it does, we assume the mapping is correct.
        # If it doesn't, we insert. The constraint should be on pii_uuid.

        cursor = self.conn.cursor()
        cursor.execute("SELECT original_value, pii_type FROM pii_decode_map WHERE pii_uuid = ?", (generated_uuid,))
        row = cursor.fetchone()

        if row:
            # UUID exists. Optionally, verify consistency (though this might be overkill and slow)
            # if row[0] != original_value or row[1] != pii_type:
            #     logger.warning(f"UUID collision or inconsistency for {generated_uuid}. Existing: ({row[0]}, {row[1]}), New: ({original_value}, {pii_type})")
            return generated_uuid
        else:
            # UUID does not exist, create new mapping
            try:
                insert_sql = """
                    INSERT INTO pii_decode_map (pii_uuid, original_value, value_for_uuid_ref, pii_type)
                    VALUES (?, ?, ?, ?)
                """
                # value_for_uuid_ref stores the value that generated the UUID
                cursor.execute(insert_sql, (generated_uuid, original_value, value_for_uuid, pii_type))
                self.conn.commit()
                logger.debug(f"Created PII mapping: {pii_type} '{original_value}' (ref: '{value_for_uuid}') -> {generated_uuid}")
                return generated_uuid
            except Exception as e: # Catch specific DuckDB exception if possible
                # Could be a race condition if another process inserted it. Try selecting again.
                logger.error(f"Error inserting PII mapping for '{original_value}': {e}. Trying to fetch again.")
                cursor.execute("SELECT pii_uuid FROM pii_decode_map WHERE pii_uuid = ?", (generated_uuid,))
                row_after_error = cursor.fetchone()
                if row_after_error:
                    return row_after_error[0]
                else:
                    # If it's still not there, the error was genuine
                    raise

    def get_original_pii(self, pii_uuid: str, requester_info: str = "UNKNOWN_REQUESTER") -> Optional[Dict[str, str]]:
        """
        Retrieves the original PII value and its type for a given UUID.
        Logs the access attempt.
        Args:
            pii_uuid: The UUID to decode.
            requester_info: Information about who or what is requesting the decode.
        Returns:
            A dictionary with 'original_value' and 'pii_type' or None if not found.
        """
        logger.info(f"PII DECODE ATTEMPT: UUID='{pii_uuid}', Requester='{requester_info}'")

        query = "SELECT original_value, pii_type FROM pii_decode_map WHERE pii_uuid = ?"
        cursor = self.conn.cursor()
        cursor.execute(query, (pii_uuid,))
        row = cursor.fetchone()

        if row:
            logger.info(f"PII DECODE SUCCESS: UUID='{pii_uuid}' retrieved type '{row[1]}'.")
            return {"original_value": row[0], "pii_type": row[1]}
        else:
            logger.warning(f"PII DECODE FAILED: UUID='{pii_uuid}' not found in pii_decode_map.")
            return None

    def replace_pii_in_text(self, text: Optional[str], pii_type: str, normalize_func: Optional[callable] = None) -> Optional[str]:
        """Replaces a single PII string with its UUID."""
        if text is None:
            return None
        if not text.strip(): # Handles empty or whitespace-only strings
            return text # Return as is, or None/empty string, based on desired behavior

        normalized_text = normalize_func(text) if normalize_func else text
        return self.get_or_create_pii_mapping(text, pii_type, normalized_value=normalized_text)

    def replace_pii_in_list(self, data_list: Optional[List[str]], pii_type: str, normalize_func: Optional[callable] = None) -> Optional[List[str]]:
        """Replaces PII strings in a list with their UUIDs."""
        if data_list is None:
            return None
        return [self.replace_pii_in_text(item, pii_type, normalize_func) for item in data_list if item is not None] # Ensure item is not None

    def replace_pii_in_dict_keys(self, data_dict: Optional[Dict[str, Any]], pii_type: str, normalize_func: Optional[callable] = None) -> Optional[Dict[str, Any]]:
        """Replaces PII strings used as keys in a dictionary with their UUIDs."""
        if data_dict is None:
            return None
        new_dict = {}
        for key, value in data_dict.items():
            new_key = self.replace_pii_in_text(key, pii_type, normalize_func)
            if new_key is not None: # Ensure key replacement was successful
                 new_dict[new_key] = value
        return new_dict

    def replace_pii_in_json_string(self, json_string: Optional[str], pii_field_specs: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Replaces PII in a JSON string based on field specifications.
        Args:
            json_string: The JSON string to process.
            pii_field_specs: A dictionary where keys are JSON field paths (e.g., 'user.name', 'details[].email')
                             and values are dicts specifying 'pii_type' and optionally 'normalize_func'.
                             Example: {
                                 "numero_processo": {"pii_type": "CASE_NUMBER", "normalize_func": normalize_case_no},
                                 "advogados_polo_ativo[]": {"pii_type": "LAWYER_FULL_STRING"}, // '[]' indicates list items
                                 "details.person.name": {"pii_type": "PARTY_NAME"}
                             }
        Returns:
            A JSON string with PII replaced, or the original if input is None.
        """
        if json_string is None:
            return None
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError:
            logger.error("Invalid JSON string provided to replace_pii_in_json_string.")
            return json_string # Or raise error

        # This is a simplified placeholder. True JSON path traversal is complex.
        # For common structures like the 'decisoes.raw_json_data', we might need specific logic.
        # For example, if raw_json_data keys are known:
        for key, spec in pii_field_specs.items():
            if key in data:
                pii_type = spec['pii_type']
                normalize_func = spec.get('normalize_func')
                if isinstance(data[key], str):
                    data[key] = self.replace_pii_in_text(data[key], pii_type, normalize_func)
                elif isinstance(data[key], list):
                    data[key] = self.replace_pii_in_list(data[key], pii_type, normalize_func)
                # Add more type handling as needed (e.g., dicts)

        return json.dumps(data)

# Example normalization functions (to be defined elsewhere, e.g., utils.py or within specific contexts)
# def normalize_lawyer_name(name: str) -> str:
#     # Placeholder for actual lawyer name normalization logic from the project
#     if name is None: return None
#     return name.lower().strip()

# def normalize_case_number(case_no: str) -> str:
#     # Placeholder
#     if case_no is None: return None
#     return "".join(filter(str.isdigit, case_no))

if __name__ == '__main__':
    # Example Usage (requires a live DuckDB connection and table)
    # import duckdb
    # conn = duckdb.connect('data/causaganha.duckdb') # Or ':memory:' for testing

    # # --- This part should be in a migration ---
    # conn.execute("""
    # CREATE TABLE IF NOT EXISTS pii_decode_map (
    #     id INTEGER PRIMARY KEY,
    #     pii_uuid VARCHAR(36) NOT NULL UNIQUE,
    #     original_value TEXT NOT NULL,
    #     value_for_uuid_ref TEXT NOT NULL, -- Stores the value that generated the UUID
    #     pii_type VARCHAR(50) NOT NULL,
    #     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    # );
    # CREATE INDEX IF NOT EXISTS idx_pii_decode_map_uuid ON pii_decode_map(pii_uuid);
    # CREATE INDEX IF NOT EXISTS idx_pii_decode_map_ref_type ON pii_decode_map(value_for_uuid_ref, pii_type);
    # """)
    # # --- End migration part ---

    # pii_manager = PiiManager(conn)

    # # Example lawyer name normalization (simplified)
    # def normalize_adv_id(name_str: str) -> str:
    #     return name_str.lower().replace("dr. ", "").replace("dra. ", "").strip()

    # lawyer_name_original = "Dr. João Advogado Exemplar"
    # lawyer_name_normalized = normalize_adv_id(lawyer_name_original)
    # lawyer_uuid = pii_manager.get_or_create_pii_mapping(lawyer_name_original, "LAWYER_ID_NORMALIZED", normalized_value=lawyer_name_normalized)
    # print(f"Original: '{lawyer_name_original}', Normalized: '{lawyer_name_normalized}', UUID: {lawyer_uuid}")

    # lawyer_name_original_2 = "DR. JOÃO ADVOGADO EXEMPLAR" # Different original, same normalized
    # lawyer_uuid_2 = pii_manager.get_or_create_pii_mapping(lawyer_name_original_2, "LAWYER_ID_NORMALIZED", normalized_value=normalize_adv_id(lawyer_name_original_2))
    # print(f"Original: '{lawyer_name_original_2}', Normalized: '{normalize_adv_id(lawyer_name_original_2)}', UUID: {lawyer_uuid_2}")
    # assert lawyer_uuid == lawyer_uuid_2

    # case_no_original = "123.456.789-00"
    # case_no_uuid = pii_manager.get_or_create_pii_mapping(case_no_original, "CASE_NUMBER", normalized_value="12345678900") # Assuming normalization
    # print(f"Original CN: '{case_no_original}', UUID: {case_no_uuid}")

    # # Test retrieving
    # retrieved_lawyer = pii_manager.get_original_pii(lawyer_uuid)
    # print(f"Retrieved for {lawyer_uuid}: {retrieved_lawyer}")
    # assert retrieved_lawyer['original_value'] == lawyer_name_original # Will be the first one stored if normalized maps to same

    # retrieved_case = pii_manager.get_original_pii(case_no_uuid)
    # print(f"Retrieved for {case_no_uuid}: {retrieved_case}")

    # # Test list replacement
    # lawyer_list = ["Dr. João Advogado Exemplar", "Dra. Maria Jurista", None, "  "]
    # uuid_list = pii_manager.replace_pii_in_list(lawyer_list, "LAWYER_ID_NORMALIZED", normalize_adv_id)
    # print(f"Original list: {lawyer_list}, UUID list: {uuid_list}")

    # # Test dict key replacement
    # ratings_dict = {"Dr. João Advogado Exemplar": 25.0, "Dra. Maria Jurista": 26.5}
    # uuid_ratings_dict = pii_manager.replace_pii_in_dict_keys(ratings_dict, "LAWYER_ID_NORMALIZED", normalize_adv_id)
    # print(f"Original dict: {ratings_dict}, UUID dict: {uuid_ratings_dict}")

    # conn.close()
    pass # End of main example
