import argparse
import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any


from src.database import CausaGanhaDB
from src.pii_manager import PiiManager
from src.utils import (
    normalize_lawyer_name,
)  # For consistency if needed, though PiiManager handles normalization internally based on type

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


# Setup basic logging for the migration script
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - PII_MIGRATION - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Helper Functions ---


def migrate_ratings_table(
    db: CausaGanhaDB, pii_manager: PiiManager, dry_run: bool = False
):
    logger.info("Starting migration for 'ratings' table...")
    try:
        # Fetch all existing ratings. Assuming advogado_id is currently the normalized name.
        # Using a direct query to get all rows as tuples/lists
        current_ratings_data = db.conn.execute(
            "SELECT advogado_id, mu, sigma, total_partidas FROM ratings"
        ).fetchall()
        logger.info(f"Found {len(current_ratings_data)} records in 'ratings' table.")

        if not current_ratings_data:
            logger.info("'ratings' table is empty. No migration needed.")
            return

        new_ratings_to_insert = []
        processed_original_ids = set()

        for i, (original_adv_id, mu, sigma, total_partidas) in enumerate(
            current_ratings_data
        ):
            if (
                original_adv_id in processed_original_ids
            ):  # Should not happen if adv_id is PK, but good check
                logger.warning(
                    f"Duplicate original_adv_id '{original_adv_id}' found in ratings. Skipping subsequent entry."
                )
                continue

            # The original_adv_id is the normalized name. This is what we store in pii_decode_map
            # as the 'original_value' for the 'LAWYER_ID_NORMALIZED' type.
            # The 'normalized_value' for PiiManager will be the same.
            new_adv_uuid = pii_manager.get_or_create_pii_mapping(
                original_value=original_adv_id,
                pii_type="LAWYER_ID_NORMALIZED",
                normalized_value=original_adv_id,  # Normalized name is the reference
            )
            new_ratings_to_insert.append((new_adv_uuid, mu, sigma, total_partidas))
            processed_original_ids.add(original_adv_id)
            if (i + 1) % 100 == 0:
                logger.info(
                    f"Processed {i + 1}/{len(current_ratings_data)} ratings for UUID mapping..."
                )

        if not dry_run:
            logger.info(
                "Deleting all existing records from 'ratings' table before re-inserting with UUIDs..."
            )
            db.conn.execute("DELETE FROM ratings")
            logger.info("All records deleted from 'ratings'.")

            logger.info(
                f"Re-inserting {len(new_ratings_to_insert)} records into 'ratings' with UUIDs as advogado_id..."
            )
            # Batch insert if possible, or one by one
            # The `update_rating` method in CausaGanhaDB handles insert if not exists.
            for adv_uuid, mu, sigma, total_partidas in new_ratings_to_insert:
                # We need to insert directly or ensure update_rating with increment=False and existing total_partidas works
                # For simplicity here, direct insert. `update_rating` logic might be too complex for just migration.
                db.conn.execute(
                    "INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                    (adv_uuid, mu, sigma, total_partidas),
                )
            db.conn.commit()  # Ensure commit after batch operations if not autocommit
            logger.info("Successfully re-inserted records into 'ratings' with UUIDs.")
        else:
            logger.info(
                f"DRY-RUN: Would delete {len(current_ratings_data)} records from 'ratings'."
            )
            logger.info(
                f"DRY-RUN: Would re-insert {len(new_ratings_to_insert)} records into 'ratings' with UUIDs."
            )

        logger.info("Migration for 'ratings' table completed.")

    except Exception as e:
        logger.error(f"Error migrating 'ratings' table: {e}", exc_info=True)
        raise


def migrate_decisoes_table(
    db: CausaGanhaDB, pii_manager: PiiManager, dry_run: bool = False
):
    logger.info("Starting migration for 'decisoes' table...")
    # Fetch all decisions row by row to manage memory, get 'id' for updates
    # This assumes 'id' is the primary key of 'decisoes'
    try:
        decision_ids = [
            row[0]
            for row in db.conn.execute("SELECT id FROM decisoes ORDER BY id").fetchall()
        ]
        total_decisions = len(decision_ids)
        logger.info(f"Found {total_decisions} records in 'decisoes' table to migrate.")

        if not total_decisions:
            logger.info(
                "'decisoes' table is empty or no IDs found. No migration needed."
            )
            return

        for i, record_id in enumerate(decision_ids):
            row_data_tuple = db.conn.execute(
                "SELECT * FROM decisoes WHERE id = ?", (record_id,)
            ).fetchone()
            if not row_data_tuple:
                logger.warning(
                    f"Could not fetch data for decisoes.id = {record_id}. Skipping."
                )
                continue

            # Get column names to map tuple to dict
            colnames = [desc[0] for desc in db.conn.description]
            row = dict(zip(colnames, row_data_tuple))

            logger.info(
                f"Migrating decisoes.id = {row['id']} ({i + 1}/{total_decisions}) ..."
            )

            updates: Dict[str, Any] = {}

            # 1. numero_processo
            if (
                row.get("numero_processo")
                and "uuid" not in str(row.get("numero_processo")).lower()
            ):  # Avoid re-processing if it looks like a UUID already
                original_np = str(row["numero_processo"])
                updates["numero_processo"] = pii_manager.get_or_create_pii_mapping(
                    original_np, "CASE_NUMBER", original_np
                )

            # 2. JSON fields: polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo
            for key, pii_type, id_type in [
                ("polo_ativo", "PARTY_NAME", None),
                ("polo_passivo", "PARTY_NAME", None),
                (
                    "advogados_polo_ativo",
                    "LAWYER_FULL_STRING",
                    "LAWYER_ID_NORMALIZED",
                ),  # We store full string UUIDs here
                (
                    "advogados_polo_passivo",
                    "LAWYER_FULL_STRING",
                    "LAWYER_ID_NORMALIZED",
                ),  # We store full string UUIDs here
            ]:
                json_str = row.get(key)
                if json_str:
                    try:
                        original_list = json.loads(json_str)
                        if not isinstance(original_list, list):
                            logger.warning(
                                f"Field {key} in decisoes.id {row['id']} is not a JSON list. Skipping PII replacement for it. Value: {json_str[:100]}"
                            )
                            continue

                        uuid_list = []
                        for item_str in original_list:
                            item_str_clean = str(item_str).strip()
                            if not item_str_clean:
                                continue

                            # For lawyers, we also ensure their normalized ID is in pii_decode_map
                            if id_type == "LAWYER_ID_NORMALIZED":
                                normalized_lawyer_id = normalize_lawyer_name(
                                    item_str_clean
                                )
                                if normalized_lawyer_id:
                                    pii_manager.get_or_create_pii_mapping(
                                        normalized_lawyer_id,
                                        id_type,
                                        normalized_lawyer_id,
                                    )

                            # All items are mapped using their respective PII type
                            uuid_list.append(
                                pii_manager.get_or_create_pii_mapping(
                                    item_str_clean, pii_type, item_str_clean
                                )
                            )
                        updates[key] = json.dumps(uuid_list)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse JSON for field {key} in decisoes.id {row['id']}. Value: {json_str[:100]}"
                        )
                    except Exception as e_json:
                        logger.error(
                            f"Error processing JSON field {key} for {row['id']}: {e_json}",
                            exc_info=True,
                        )

            # 3. raw_json_data - This is complex. For now, let's assume it's a JSON representation
            # of the original decision_data_original structure. We'll replace known PII fields.
            raw_json_str = row.get("raw_json_data")
            if raw_json_str:
                try:
                    raw_data = json.loads(raw_json_str)
                    # This is a simplified replacement. A more robust solution would use json path based replacement.
                    if raw_data.get("numero_processo"):
                        raw_data["numero_processo"] = (
                            pii_manager.get_or_create_pii_mapping(
                                str(raw_data["numero_processo"]),
                                "CASE_NUMBER",
                                str(raw_data["numero_processo"]),
                            )
                        )

                    for polo_key in ["polo_ativo", "polo_passivo"]:
                        if raw_data.get(polo_key):
                            polo_list = raw_data[polo_key]
                            if isinstance(polo_list, str):
                                polo_list = [polo_list]  # handle single string
                            if isinstance(polo_list, list):
                                raw_data[polo_key] = [
                                    pii_manager.get_or_create_pii_mapping(
                                        str(name), "PARTY_NAME", str(name)
                                    )
                                    for name in polo_list
                                    if name and str(name).strip()
                                ]

                    for adv_key in ["advogados_polo_ativo", "advogados_polo_passivo"]:
                        if raw_data.get(adv_key):
                            adv_list = raw_data[adv_key]
                            if isinstance(adv_list, str):
                                adv_list = [adv_list]  # handle single string
                            if isinstance(adv_list, list):
                                temp_adv_uuids = []
                                for adv_name_str in adv_list:
                                    adv_name_str_clean = str(adv_name_str).strip()
                                    if not adv_name_str_clean:
                                        continue
                                    # Ensure normalized ID is mapped
                                    norm_id = normalize_lawyer_name(adv_name_str_clean)
                                    if norm_id:
                                        pii_manager.get_or_create_pii_mapping(
                                            norm_id, "LAWYER_ID_NORMALIZED", norm_id
                                        )
                                    # Store full string UUID in raw_json_data
                                    temp_adv_uuids.append(
                                        pii_manager.get_or_create_pii_mapping(
                                            adv_name_str_clean,
                                            "LAWYER_FULL_STRING",
                                            adv_name_str_clean,
                                        )
                                    )
                                raw_data[adv_key] = temp_adv_uuids
                    updates["raw_json_data"] = json.dumps(raw_data)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse JSON for raw_json_data in decisoes.id {row['id']}. Value: {raw_json_str[:100]}"
                    )
                except Exception as e_rawjson:
                    logger.error(
                        f"Error processing raw_json_data for {row['id']}: {e_rawjson}",
                        exc_info=True,
                    )

            if updates and not dry_run:
                set_clauses = ", ".join([f"{k} = ?" for k in updates.keys()])
                params = list(updates.values()) + [row["id"]]
                try:
                    db.conn.execute(
                        f"UPDATE decisoes SET {set_clauses} WHERE id = ?", params
                    )
                except Exception as e_update:
                    logger.error(
                        f"Failed to update decisoes.id {row['id']}: {e_update}",
                        exc_info=True,
                    )

            elif updates and dry_run:
                logger.info(
                    f"DRY-RUN: Would update decisoes.id {row['id']} with {len(updates)} changes."
                )

        if not dry_run:
            db.conn.commit()
        logger.info("Migration for 'decisoes' table completed.")
    except Exception as e:
        logger.error(f"Error migrating 'decisoes' table: {e}", exc_info=True)
        raise


def migrate_partidas_table(
    db: CausaGanhaDB, pii_manager: PiiManager, dry_run: bool = False
):
    logger.info("Starting migration for 'partidas' table...")
    try:
        # Fetch all partidas, identified by 'id'
        partida_ids = [
            row[0]
            for row in db.conn.execute("SELECT id FROM partidas ORDER BY id").fetchall()
        ]
        total_partidas = len(partida_ids)
        logger.info(f"Found {total_partidas} records in 'partidas' table to migrate.")

        if not total_partidas:
            logger.info("'partidas' table is empty. No migration needed.")
            return

        for i, record_id in enumerate(partida_ids):
            row_data_tuple = db.conn.execute(
                "SELECT * FROM partidas WHERE id = ?", (record_id,)
            ).fetchone()
            if not row_data_tuple:
                logger.warning(
                    f"Could not fetch data for partidas.id = {record_id}. Skipping."
                )
                continue

            colnames = [desc[0] for desc in db.conn.description]
            row = dict(zip(colnames, row_data_tuple))

            logger.info(
                f"Migrating partidas.id = {row['id']} ({i + 1}/{total_partidas}) ..."
            )
            updates: Dict[str, Any] = {}

            # 1. numero_processo
            if (
                row.get("numero_processo")
                and "uuid" not in str(row.get("numero_processo")).lower()
            ):
                original_np = str(row["numero_processo"])
                updates["numero_processo"] = pii_manager.get_or_create_pii_mapping(
                    original_np, "CASE_NUMBER", original_np
                )

            # 2. equipe_a_ids, equipe_b_ids (JSON list of normalized lawyer names)
            for key in ["equipe_a_ids", "equipe_b_ids"]:
                json_str = row.get(key)
                if json_str:
                    try:
                        original_list = json.loads(json_str)
                        if not isinstance(original_list, list):
                            logger.warning(
                                f"Field {key} in partidas.id {row['id']} is not a JSON list. Skipping PII replacement. Value: {json_str[:100]}"
                            )
                            continue
                        # These are normalized lawyer names, map them to LAWYER_ID_NORMALIZED UUIDs
                        uuid_list = [
                            pii_manager.get_or_create_pii_mapping(
                                str(norm_name), "LAWYER_ID_NORMALIZED", str(norm_name)
                            )
                            for norm_name in original_list
                            if norm_name and str(norm_name).strip()
                        ]
                        updates[key] = json.dumps(uuid_list)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse JSON for field {key} in partidas.id {row['id']}. Value: {json_str[:100]}"
                        )
                    except Exception as e_json_eq:
                        logger.error(
                            f"Error processing JSON field {key} for {row['id']}: {e_json_eq}",
                            exc_info=True,
                        )

            # 3. Ratings dicts (keys are normalized lawyer names)
            for key in [
                "ratings_equipe_a_antes",
                "ratings_equipe_b_antes",
                "ratings_equipe_a_depois",
                "ratings_equipe_b_depois",
            ]:
                json_str = row.get(key)
                if json_str:
                    try:
                        original_dict = json.loads(json_str)
                        if not isinstance(original_dict, dict):
                            logger.warning(
                                f"Field {key} in partidas.id {row['id']} is not a JSON dict. Skipping PII replacement. Value: {json_str[:100]}"
                            )
                            continue

                        uuid_keyed_dict = {
                            pii_manager.get_or_create_pii_mapping(
                                str(norm_name_key),
                                "LAWYER_ID_NORMALIZED",
                                str(norm_name_key),
                            ): value
                            for norm_name_key, value in original_dict.items()
                            if norm_name_key and str(norm_name_key).strip()
                        }
                        updates[key] = json.dumps(uuid_keyed_dict)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse JSON for field {key} in partidas.id {row['id']}. Value: {json_str[:100]}"
                        )
                    except Exception as e_json_ratings:
                        logger.error(
                            f"Error processing JSON field {key} for {row['id']}: {e_json_ratings}",
                            exc_info=True,
                        )

            if updates and not dry_run:
                set_clauses = ", ".join([f"{k} = ?" for k in updates.keys()])
                params = list(updates.values()) + [row["id"]]
                try:
                    db.conn.execute(
                        f"UPDATE partidas SET {set_clauses} WHERE id = ?", params
                    )
                except Exception as e_update_partida:
                    logger.error(
                        f"Failed to update partidas.id {row['id']}: {e_update_partida}",
                        exc_info=True,
                    )

            elif updates and dry_run:
                logger.info(
                    f"DRY-RUN: Would update partidas.id {row['id']} with {len(updates)} changes."
                )

        if not dry_run:
            db.conn.commit()
        logger.info("Migration for 'partidas' table completed.")
    except Exception as e:
        logger.error(f"Error migrating 'partidas' table: {e}", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Migrates existing PII in the database to UUID representations.",
        epilog="WARNING: This is a destructive operation. Backup your database before running.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=project_root / "data" / "causaganha.duckdb",
        help="Path to the DuckDB database file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the migration without making actual changes to the database.",
    )
    parser.add_argument(
        "--tables",
        type=str,
        nargs="+",  # one or more table names
        choices=["ratings", "decisoes", "partidas", "all"],
        default=["all"],
        help="Specify which tables to migrate (ratings, decisoes, partidas, or all).",
    )

    args = parser.parse_args()

    if not args.db_path.exists():
        logger.error(f"Database file not found at: {args.db_path}")
        sys.exit(1)

    if not args.dry_run:
        confirm = input(
            f"WARNING: This script will modify the database '{args.db_path}' in place.\n"
            "It is STRONGLY recommended to backup your database before proceeding.\n"
            "Type 'YES_MIGRATE_PII' to continue: "
        )
        if confirm != "YES_MIGRATE_PII":
            logger.info("Migration aborted by user.")
            sys.exit(0)

    logger.info(f"{'DRY RUN' if args.dry_run else 'LIVE RUN'} selected.")
    logger.info(f"Target database: {args.db_path}")
    logger.info(f"Tables to migrate: {', '.join(args.tables)}")

    db = None
    try:
        db = CausaGanhaDB(db_path=args.db_path)
        db.connect()  # Runs migrations, ensuring pii_decode_map table exists
        pii_manager = PiiManager(db.conn)

        # Start a transaction if not in dry_run and if supported/desired
        if not args.dry_run:
            logger.info("Beginning database transaction for PII migration.")
            try:
                db.conn.begin()  # Explicit transaction start
            except Exception as e_tx_begin:  # DuckDB might autocommit or handle transactions differently
                logger.warning(
                    f"Could not explicitly begin transaction (may be normal for DuckDB): {e_tx_begin}"
                )

        tables_to_migrate = args.tables
        if "all" in tables_to_migrate:
            tables_to_migrate = ["ratings", "decisoes", "partidas"]  # Specific order

        # Migrate ratings first to populate lawyer UUIDs that might be referenced by others
        if "ratings" in tables_to_migrate:
            migrate_ratings_table(db, pii_manager, args.dry_run)

        # Then migrate decisoes
        if "decisoes" in tables_to_migrate:
            migrate_decisoes_table(db, pii_manager, args.dry_run)

        # Finally, migrate partidas, which references lawyer UUIDs and case number UUIDs
        if "partidas" in tables_to_migrate:
            migrate_partidas_table(db, pii_manager, args.dry_run)

        if not args.dry_run:
            logger.info("Committing transaction.")
            db.conn.commit()
        else:
            logger.info("DRY-RUN: No transaction to commit.")

        logger.info("PII data migration process completed.")

    except Exception as e:
        logger.error(f"An error occurred during the PII migration: {e}", exc_info=True)
        if not args.dry_run and db and db.conn:
            try:
                logger.error("Attempting to rollback transaction due to error.")
                db.conn.rollback()  # Rollback on error
            except Exception as e_tx_rollback:
                logger.error(f"Failed to rollback transaction: {e_tx_rollback}")
        sys.exit(1)
    finally:
        if db and db.conn:
            db.close()
            logger.info("Database connection closed.")


if __name__ == "__main__":
    main()
