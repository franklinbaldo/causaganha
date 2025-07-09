"""
Simple backup and export functions to replace the complex sync system.

This module provides straightforward database backup and export functionality
without the complexity of distributed locking and sync protocols.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb

# Simple backup function
def backup_database_before_changes(
    db_path: Path = Path("data/causaganha.duckdb"),
    backup_dir: Path = Path("data/backups")
) -> Path:
    """
    Create timestamped backup before modifications.
    
    Args:
        db_path: Path to the database file
        backup_dir: Directory to store backups
        
    Returns:
        Path to the created backup file
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"causaganha_{timestamp}.duckdb"
    backup_path = backup_dir / backup_filename
    
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
    else:
        print(f"⚠️  Database not found at: {db_path}")
        
    return backup_path


def export_to_parquet(
    db_path: Path = Path("data/causaganha.duckdb"),
    export_dir: Path = Path("data/exports")
) -> Dict[str, Path]:
    """
    Export database tables to parquet format.
    
    Args:
        db_path: Path to the database file
        export_dir: Directory to store exports
        
    Returns:
        Dictionary mapping table names to parquet file paths
    """
    export_dir.mkdir(parents=True, exist_ok=True)
    
    if not db_path.exists():
        print(f"⚠️  Database not found at: {db_path}")
        return {}
    
    conn = duckdb.connect(str(db_path))
    
    # Get all tables
    tables = conn.execute("SHOW TABLES").fetchall()
    
    if not tables:
        print("⚠️  No tables found in database")
        return {}
    
    exported_files = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for table_name, in tables:
        # Check if table has data
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if count == 0:
            print(f"⚠️  Table {table_name} is empty, skipping...")
            continue
            
        parquet_filename = f"{table_name}_{timestamp}.parquet"
        parquet_path = export_dir / parquet_filename
        
        try:
            # Export using DuckDB's native COPY command
            conn.execute(f"""
                COPY {table_name} TO '{parquet_path}' 
                (FORMAT PARQUET, COMPRESSION SNAPPY)
            """)
            
            exported_files[table_name] = parquet_path
            print(f"✅ Exported {table_name} to: {parquet_path}")
            
        except Exception as e:
            print(f"❌ Failed to export {table_name}: {e}")
    
    conn.close()
    
    print(f"📊 Exported {len(exported_files)} tables to parquet format")
    return exported_files


def upload_to_ia_simple(
    parquet_files: Dict[str, Path],
    collection_prefix: str = "causaganha"
) -> Dict[str, str]:
    """
    Simple upload to Internet Archive (no locking complexity).
    
    Args:
        parquet_files: Dictionary of table_name -> parquet_path
        collection_prefix: Prefix for IA collection names
        
    Returns:
        Dictionary mapping table names to IA URLs
    """
    try:
        from internetarchive import upload
        import os
        
        # Check for IA credentials
        access_key = os.getenv("IA_ACCESS_KEY")
        secret_key = os.getenv("IA_SECRET_KEY")
        
        if not access_key or not secret_key:
            print("⚠️  IA credentials not found, skipping upload")
            return {}
        
        uploaded_urls = {}
        
        for table_name, parquet_path in parquet_files.items():
            if not parquet_path.exists():
                print(f"⚠️  File not found: {parquet_path}")
                continue
            
            # Simple identifier based on table name and date
            timestamp = datetime.now().strftime("%Y%m%d")
            identifier = f"{collection_prefix}-{table_name}-{timestamp}"
            
            # Simple metadata
            metadata = {
                "title": f"CausaGanha {table_name.title()} Dataset",
                "description": f"Parquet dataset from CausaGanha {table_name} table, exported on {datetime.now().strftime('%Y-%m-%d')}",
                "collection": "opensource_data",
                "mediatype": "data",
                "subject": ["legal", "judicial", "brazil", "parquet", "dataset"],
                "creator": "CausaGanha Pipeline",
                "date": datetime.now().isoformat(),
            }
            
            try:
                # Simple upload - no locking needed
                upload(
                    identifier=identifier,
                    files={parquet_path.name: str(parquet_path)},
                    metadata=metadata,
                    access_key=access_key,
                    secret_key=secret_key,
                    verbose=True,
                    queue_derive=False
                )
                
                url = f"https://archive.org/details/{identifier}"
                uploaded_urls[table_name] = url
                print(f"✅ Uploaded {table_name} to: {url}")
                
            except Exception as e:
                print(f"❌ Failed to upload {table_name}: {e}")
        
        return uploaded_urls
        
    except ImportError:
        print("⚠️  internetarchive library not available, skipping upload")
        return {}


def export_and_upload_to_ia(
    db_path: Path = Path("data/causaganha.duckdb"),
    export_dir: Path = Path("data/exports"),
    collection_prefix: str = "causaganha"
) -> Dict[str, str]:
    """
    Export database to parquet and upload to Internet Archive.
    
    This is a simple, one-step function that replaces the complex sync system.
    
    Args:
        db_path: Path to the database file
        export_dir: Directory to store exports
        collection_prefix: Prefix for IA collection names
        
    Returns:
        Dictionary mapping table names to IA URLs
    """
    print("🚀 Starting simple export and upload...")
    
    # Step 1: Export to parquet
    exported_files = export_to_parquet(db_path, export_dir)
    
    if not exported_files:
        print("⚠️  No files exported, skipping upload")
        return {}
    
    # Step 2: Upload to IA
    uploaded_urls = upload_to_ia_simple(exported_files, collection_prefix)
    
    print(f"✅ Simple export and upload completed!")
    print(f"📊 Exported {len(exported_files)} tables, uploaded {len(uploaded_urls)} successfully")
    
    return uploaded_urls


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple backup and export tools")
    parser.add_argument("action", choices=["backup", "export", "upload"], help="Action to perform")
    parser.add_argument("--db-path", default="data/causaganha.duckdb", help="Database path")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        backup_database_before_changes(Path(args.db_path))
    elif args.action == "export":
        export_to_parquet(Path(args.db_path))
    elif args.action == "upload":
        export_and_upload_to_ia(Path(args.db_path))