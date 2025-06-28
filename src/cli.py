"""CausaGanha CLI - Modern command-line interface for judicial document processing."""

import typer
from typing import Optional, List  # Added Dict, Any, Tuple
from pathlib import Path
import csv
from urllib.parse import urlparse
import re
from datetime import datetime
import json
import asyncio
import aiohttp
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor

from database import CausaGanhaDB
from config import load_config
from extractor import GeminiExtractor

app = typer.Typer(
    name="causaganha",
    help="Judicial document processing pipeline with OpenSkill rating system",
    no_args_is_help=True,
)

# Global state
config = load_config()
db = CausaGanhaDB(Path(config["database"]["path"]))


def extract_tribunal_from_url(url: str) -> str:
    """Extract tribunal domain from URL."""
    return urlparse(url).netloc.lower()


def validate_tribunal_url(url: str) -> bool:
    """Validate that URL is from a Brazilian judicial domain (.jus.br)."""
    domain = urlparse(url).netloc.lower()
    return domain.endswith(".jus.br")


def extract_date_from_url(url: str) -> Optional[str]:
    """Extract date from URL patterns."""
    # Common date patterns in URLs
    date_patterns = [
        r"diario(\d{8})",  # diario20250626
        r"(\d{8})",  # 20250626
        r"(\d{4}-\d{2}-\d{2})",  # 2025-06-26
        r"(\d{2}-\d{2}-\d{4})",  # 26-06-2025
    ]

    for pattern in date_patterns:
        match = re.search(pattern, url)
        if match:
            date_str = match.group(1)

            # Try to parse different formats
            try:
                if len(date_str) == 8 and date_str.isdigit():
                    # YYYYMMDD
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    return date_obj.strftime("%Y-%m-%d")
                elif "-" in date_str:
                    if date_str.count("-") == 2:
                        parts = date_str.split("-")
                        if len(parts[0]) == 4:
                            # YYYY-MM-DD
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            return date_obj.strftime("%Y-%m-%d")
                        else:
                            # DD-MM-YYYY
                            date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                            return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return None


@app.command()
def queue(
    url: Optional[str] = typer.Option(None, "--url", help="Single URL to queue"),
    from_csv: Optional[Path] = typer.Option(
        None, "--from-csv", help="CSV file with URLs"
    ),
):
    """Add documents to processing queue."""
    if not url and not from_csv:
        typer.echo("❌ Either --url or --from-csv is required", err=True)
        raise typer.Exit(1)

    if url and from_csv:
        typer.echo("❌ Cannot use both --url and --from-csv", err=True)
        raise typer.Exit(1)

    # Initialize job queue table if it doesn't exist
    db.conn.execute("""
        CREATE TABLE IF NOT EXISTS job_queue (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL UNIQUE,
            date DATE,
            tribunal TEXT,
            filename TEXT,
            metadata JSON,
            status TEXT DEFAULT 'queued',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            ia_identifier TEXT, # Will store the MASTER IA item ID
            ia_remote_filename TEXT, # Full path of the file within the master IA item
            analyze_result JSON,
            score_updated BOOLEAN DEFAULT FALSE,
            ia_metadata_synced BOOLEAN DEFAULT FALSE
        )
    """)

    urls_to_queue = []

    if url:
        # Single URL
        if not validate_tribunal_url(url):
            typer.echo(f"❌ Only .jus.br domains are allowed: {url}", err=True)
            raise typer.Exit(1)

        tribunal = extract_tribunal_from_url(url)
        date = extract_date_from_url(url)
        filename = Path(urlparse(url).path).name

        urls_to_queue.append(
            {
                "url": url,
                "date": date,
                "tribunal": tribunal,
                "filename": filename,
                "metadata": {},
            }
        )

    elif from_csv:
        # CSV file
        if not from_csv.exists():
            typer.echo(f"❌ CSV file not found: {from_csv}", err=True)
            raise typer.Exit(1)

        with open(from_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if "url" not in reader.fieldnames:
                typer.echo("❌ CSV must have 'url' column", err=True)
                raise typer.Exit(1)

            for row in reader:
                url = row["url"].strip()
                if not url:
                    continue

                # Validate .jus.br domain
                if not validate_tribunal_url(url):
                    typer.echo(f"❌ Skipping non-.jus.br URL: {url}")
                    continue

                # Use CSV date if provided, otherwise extract from URL
                date = row.get("date", "").strip() or extract_date_from_url(url)
                tribunal = row.get("tribunal", "").strip() or extract_tribunal_from_url(
                    url
                )
                filename = (
                    row.get("filename", "").strip() or Path(urlparse(url).path).name
                )

                urls_to_queue.append(
                    {
                        "url": url,
                        "date": date,
                        "tribunal": tribunal,
                        "filename": filename,
                        "metadata": {},
                    }
                )

    # Insert into queue
    queued_count = 0
    skipped_count = 0

    for item in urls_to_queue:
        try:
            db.conn.execute(
                """
                INSERT INTO job_queue (url, date, tribunal, filename, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    item["url"],
                    item["date"],
                    item["tribunal"],
                    item["filename"],
                    json.dumps(item["metadata"]),
                ],
            )
            queued_count += 1

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                skipped_count += 1
            else:
                typer.echo(f"❌ Error queuing {item['url']}: {e}", err=True)

    typer.echo(f"✅ Queued {queued_count} items")
    if skipped_count > 0:
        typer.echo(f"⚠️  Skipped {skipped_count} duplicate URLs")


@app.command()
def archive(
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Maximum number of items to process"
    ),
    force: bool = typer.Option(
        False, "--force", help="Reprocess items that are already archived"
    ),
):
    """Download queued documents and store in Internet Archive."""
    # Get queued items
    if force:
        query = "SELECT * FROM job_queue WHERE status IN ('queued', 'failed') OR status = 'archived'"
    else:
        query = "SELECT * FROM job_queue WHERE status IN ('queued', 'failed')"

    if limit:
        query += f" LIMIT {limit}"

    result = db.conn.execute(query).fetchall()

    if not result:
        typer.echo("📦 No items to archive")
        return

    typer.echo(f"📦 Archiving {len(result)} items...")

    # Create data directory
    data_dir = Path("data")
    diarios_dir = data_dir / "diarios"
    diarios_dir.mkdir(parents=True, exist_ok=True)

    asyncio.run(_archive_items_async(result, data_dir))

    typer.echo("✅ Archive process completed!")


async def _archive_items_async(items, data_dir: Path):
    """Async processing of archive items."""
    # Create aiohttp session with timeout
    timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Process items concurrently with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent downloads

        tasks = []
        for item in items:
            task = _archive_single_item(session, semaphore, item, data_dir)
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)


async def _archive_single_item(
    session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, item, data_dir: Path
):
    """Archive a single item: download and upload to IA."""
    async with semaphore:
        url = item[1]  # url column
        date_str = item[2]  # date column
        tribunal = item[3]  # tribunal column
        filename = item[4]  # filename column

        # Generate IA identifier
        if date_str:
            # Use date in identifier
            date_obj = datetime.fromisoformat(date_str)
            ia_identifier = f"tjro-diario-{date_obj.strftime('%Y-%m-%d')}"
        else:
            # Use hash of URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            ia_identifier = f"diario-{tribunal.replace('.', '-')}-{url_hash}"

        # Download PDF
        try:
            local_path = data_dir / "diarios" / (filename or f"{ia_identifier}.pdf")

            # Skip if already exists and valid
            if local_path.exists() and local_path.stat().st_size > 1000:
                typer.echo(f"⏭️  Skipping existing: {local_path.name}")
            else:
                typer.echo(f"⬇️  Downloading: {url}")

                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()

                        # Validate PDF
                        if not content.startswith(b"%PDF"):
                            raise ValueError("Downloaded content is not a valid PDF")

                        # Save file
                        with open(local_path, "wb") as f:
                            f.write(content)

                        typer.echo(
                            f"✅ Downloaded: {local_path.name} ({len(content):,} bytes)"
                        )
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}",
                        )

            # Upload to IA
            success = await _upload_to_ia_async(
                local_path, ia_identifier, url, tribunal, date_str
            )

            if success:
                # Update database status
                db.conn.execute(
                    """
                    UPDATE job_queue 
                    SET status = 'archived', ia_identifier = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                """,
                    [ia_identifier, url],
                )

                typer.echo(f"🌐 Uploaded to IA: {ia_identifier}")

                # Cleanup local file
                try:
                    local_path.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
            else:
                # Mark as failed
                db.conn.execute(
                    """
                    UPDATE job_queue 
                    SET status = 'failed', updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                """,
                    [url],
                )

        except Exception as e:
            typer.echo(f"❌ Failed to archive {url}: {e}")

            # Mark as failed
            db.conn.execute(
                """
                UPDATE job_queue 
                SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE url = ?
            """,
                [str(e), url],
            )


async def _upload_to_ia_async(
    local_path: Path,
    ia_identifier: str,
    original_url: str,
    tribunal: str,
    date_str: Optional[str],
) -> bool:
    """Upload file to Internet Archive."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(
            executor,
            _upload_to_ia_sync,
            local_path,
            ia_identifier,
            original_url,
            tribunal,
            date_str,
        )


def _upload_to_ia_sync(
    local_path: Path,
    ia_identifier: str,
    original_url: str,
    tribunal: str,
    date_str: Optional[str],
) -> bool:
    """Synchronous IA upload."""
    try:
        # Prepare metadata
        metadata = {
            "title": f"Diário Oficial - {tribunal}",
            "creator": "CausaGanha",
            "subject": "judicial;legal;brazil;court;decisions",
            "description": f"Diário oficial from {tribunal}",
            "language": "por",
            "mediatype": "texts",
            "collection": "opensource",
            "originalurl": original_url,
            "tribunal": tribunal,
        }

        if date_str:
            metadata["date"] = date_str

        # Build IA command
        ia_cmd = ["ia", "upload", ia_identifier, str(local_path)]

        # Add metadata
        for key, value in metadata.items():
            if value:
                ia_cmd.extend([f"--metadata={key}:{value}"])

        # Execute upload
        result = subprocess.run(
            ia_cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes
        )

        return result.returncode == 0

    except Exception as e:
        typer.echo(f"❌ IA upload error: {e}")
        return False


@app.command()
def analyze(
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Maximum number of items to process"
    ),
    force: bool = typer.Option(
        False, "--force", help="Reprocess items that are already analyzed"
    ),
):
    """Extract information from archived documents using LLM."""
    # Get archived items ready for analysis
    if force:
        query = "SELECT * FROM job_queue WHERE status IN ('archived', 'failed') OR status = 'analyzed'"
    else:
        query = "SELECT * FROM job_queue WHERE status = 'archived'"

    if limit:
        query += f" LIMIT {limit}"

    result = db.conn.execute(query).fetchall()

    if not result:
        typer.echo("🔍 No items to analyze")
        return

    typer.echo(f"🔍 Analyzing {len(result)} items...")

    # Initialize Gemini extractor
    extractor = GeminiExtractor()

    if not extractor.gemini_configured:
        typer.echo(
            "❌ Gemini not configured. Please set GEMINI_API_KEY environment variable."
        )
        typer.echo("💡 Analysis requires a valid Gemini API key for LLM extraction.")
        typer.echo("   Get your API key from: https://aistudio.google.com/app/apikey")
        return

    # Create output directories
    data_dir = Path("data")
    temp_dir = data_dir / "temp"
    json_output_dir = data_dir / "json_extractions"
    json_output_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    failed = 0

    for item in result:
        url = item[1]  # url column
        ia_identifier = item[10]  # ia_identifier column

        if not ia_identifier:
            typer.echo(f"⚠️  Skipping item without IA identifier: {url}")
            continue

        try:
            # Download from IA and analyze
            success = _analyze_single_item(
                extractor, ia_identifier, url, json_output_dir, temp_dir
            )

            if success:
                # Update database status
                db.conn.execute(
                    """
                    UPDATE job_queue 
                    SET status = 'analyzed', updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                """,
                    [url],
                )

                typer.echo(f"✅ Analyzed: {ia_identifier}")
                processed += 1
            else:
                # Mark as failed
                db.conn.execute(
                    """
                    UPDATE job_queue 
                    SET status = 'failed', updated_at = CURRENT_TIMESTAMP
                    WHERE url = ?
                """,
                    [url],
                )
                failed += 1

        except Exception as e:
            typer.echo(f"❌ Failed to analyze {ia_identifier}: {e}")

            # Mark as failed
            db.conn.execute(
                """
                UPDATE job_queue 
                SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE url = ?
            """,
                [str(e), url],
            )
            failed += 1

    typer.echo(f"🔍 Analysis completed: {processed} processed, {failed} failed")


def _analyze_single_item(
    extractor: GeminiExtractor,
    ia_identifier: str,
    url: str,
    json_output_dir: Path,
    temp_dir: Path,
) -> bool:
    """Analyze a single item from Internet Archive."""
    try:
        # Download PDF from IA
        ia_url = f"https://archive.org/download/{ia_identifier}/{ia_identifier}.pdf"

        # Try to find the actual filename from IA
        import requests

        try:
            # Get IA metadata to find actual filename
            metadata_url = f"https://archive.org/metadata/{ia_identifier}"
            response = requests.get(metadata_url, timeout=30)
            if response.status_code == 200:
                metadata = response.json()
                files = metadata.get("files", [])
                pdf_files = [f for f in files if f.get("name", "").endswith(".pdf")]
                if pdf_files:
                    actual_filename = pdf_files[0]["name"]
                    ia_url = f"https://archive.org/download/{ia_identifier}/{actual_filename}"
        except Exception:
            pass  # Use default URL if metadata lookup fails

        # Download PDF to temp location
        temp_pdf = temp_dir / f"{ia_identifier}.pdf"
        temp_dir.mkdir(parents=True, exist_ok=True)

        response = requests.get(ia_url, timeout=300)
        if response.status_code != 200:
            raise Exception(f"Failed to download from IA: HTTP {response.status_code}")

        # Validate PDF content
        if not response.content.startswith(b"%PDF"):
            raise Exception("Downloaded content is not a valid PDF")

        # Save to temp file
        with open(temp_pdf, "wb") as f:
            f.write(response.content)

        typer.echo(
            f"⬇️  Downloaded from IA: {ia_identifier} ({len(response.content):,} bytes)"
        )

        # Extract with Gemini
        json_path = extractor.extract_and_save_json(temp_pdf, json_output_dir)

        if json_path and json_path.exists():
            # Validate that we got real data, not dummy data
            if _validate_extraction_results(json_path):
                typer.echo(f"📄 Extracted to: {json_path.name}")

                # Store JSON results in database
                _store_extraction_results(json_path, ia_identifier)

                return True
            else:
                raise Exception(
                    "Extraction produced dummy/invalid data - check Gemini API configuration"
                )
        else:
            raise Exception("Gemini extraction failed")

    except Exception as e:
        typer.echo(f"❌ Analysis error for {ia_identifier}: {e}")
        return False
    finally:
        # Cleanup temp file
        try:
            if temp_pdf.exists():
                temp_pdf.unlink()
        except Exception:
            pass


def _validate_extraction_results(json_path: Path) -> bool:
    """Validate extraction results to detect dummy data."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check for dummy data indicators
        if isinstance(data, dict):
            # Single decision format
            if data.get("status") == "dummy_data_gemini_not_configured":
                return False
            if data.get("numero_processo") == "0000000-00.0000.0.00.0000":
                return False
            if data.get("data_decisao") == "1900-01-01":
                return False
        elif isinstance(data, list):
            # Multiple decisions format
            if not data:  # Empty list
                return False
            for decision in data:
                if isinstance(decision, dict):
                    if decision.get("status") == "dummy_data_gemini_not_configured":
                        return False
                    if decision.get("numero_processo") == "0000000-00.0000.0.00.0000":
                        return False
                    if decision.get("data_decisao") == "1900-01-01":
                        return False

        return True

    except Exception:
        return False


def _store_extraction_results(json_path: Path, ia_identifier: str):
    """Store extraction results in the database."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            extraction_data = json.load(f)

        # Store in json_files table
        db.conn.execute(
            """
            INSERT OR REPLACE INTO json_files (filename, content, source_type, created_at)
            VALUES (?, ?, 'gemini_extraction', CURRENT_TIMESTAMP)
        """,
            [json_path.name, json.dumps(extraction_data)],
        )

        # If extraction contains decisions, store them in decisoes table
        if isinstance(extraction_data, list):
            decisions = extraction_data
        elif isinstance(extraction_data, dict) and "decisions" in extraction_data:
            decisions = extraction_data["decisions"]
        else:
            decisions = []

        for decision in decisions:
            if isinstance(decision, dict) and "numero_processo" in decision:
                try:
                    db.conn.execute(
                        """
                        INSERT OR REPLACE INTO decisoes (
                            numero_processo, json_source_file, tipo_decisao, resultado,
                            polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo,
                            resumo, raw_json_data, processed_for_openskill, validation_status,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE, 'pending', CURRENT_TIMESTAMP)
                    """,
                        [
                            decision.get("numero_processo", ""),
                            json_path.name,
                            decision.get("tipo_decisao", ""),
                            decision.get("resultado", ""),
                            json.dumps(
                                decision.get("partes", {}).get("requerente", [])
                            ),
                            json.dumps(decision.get("partes", {}).get("requerido", [])),
                            json.dumps(
                                decision.get("advogados", {}).get("requerente", [])
                            ),
                            json.dumps(
                                decision.get("advogados", {}).get("requerido", [])
                            ),
                            decision.get("resumo", ""),
                            json.dumps(decision),
                        ],
                    )
                except Exception as e:
                    typer.echo(
                        f"⚠️  Failed to store decision {decision.get('numero_processo', 'unknown')}: {e}"
                    )

    except Exception as e:
        typer.echo(f"⚠️  Failed to store extraction results: {e}")


@app.command()
def score(
    force: bool = typer.Option(
        False, "--force", help="Recalculate all ratings from scratch"
    ),
):
    """Generate OpenSkill ratings from analyzed data."""
    # Import OpenSkill functionality
    import sys

    sys.path.append(".")

    # Import OpenSkill functionality
    import sys

    sys.path.append(".")

    try:
        from openskill_rating import get_openskill_model
    except ImportError:
        typer.echo("❌ OpenSkill rating module not found")
        return

    # Import create_rating and rate_teams here to avoid F821 and F401

    # Get analyzed items that need scoring
    if force:
        # Reset all processed flags
        db.conn.execute("UPDATE decisoes SET processed_for_openskill = FALSE")
        typer.echo("🔄 Reset all decisions for reprocessing")

    # Get unprocessed decisions (excluding dummy data)
    result = db.conn.execute("""
        SELECT id, numero_processo, advogados_polo_ativo, advogados_polo_passivo, resultado
        FROM decisoes 
        WHERE processed_for_openskill = FALSE 
        AND validation_status = 'valid'
        AND resultado IS NOT NULL
        AND resultado != ''
        AND numero_processo != '0000000-00.0000.0.00.0000'
        AND raw_json_data NOT LIKE '%dummy_data_gemini_not_configured%'
    """).fetchall()

    if not result:
        typer.echo("⭐ No decisions to process for scoring")
        return

    typer.echo(f"⭐ Processing {len(result)} decisions for OpenSkill rating...")

    # Initialize OpenSkill model
    os_model = get_openskill_model(config.get("openskill", {}))

    processed = 0
    failed = 0

    for decision in result:
        decision_id = decision[0]
        numero_processo = decision[1]
        advogados_ativo_json = decision[2]
        advogados_passivo_json = decision[3]
        resultado = decision[4]

        try:
            success = _process_decision_for_rating(
                os_model,
                decision_id,
                numero_processo,
                advogados_ativo_json,
                advogados_passivo_json,
                resultado,
            )

            if success:
                # Mark as processed
                db.conn.execute(
                    """
                    UPDATE decisoes 
                    SET processed_for_openskill = TRUE, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    [decision_id],
                )
                processed += 1
            else:
                failed += 1

        except Exception as e:
            typer.echo(f"❌ Failed to process decision {numero_processo}: {e}")
            failed += 1

    # Update job queue status for analyzed items
    db.conn.execute("""
        UPDATE job_queue 
        SET status = 'scored', updated_at = CURRENT_TIMESTAMP
        WHERE status = 'analyzed'
    """)

    typer.echo(f"⭐ Scoring completed: {processed} processed, {failed} failed")

    # Show rating statistics
    _show_rating_stats()


def _process_decision_for_rating(
    os_model,
    decision_id: int,
    numero_processo: str,
    advogados_ativo_json: str,
    advogados_passivo_json: str,
    resultado: str,
) -> bool:
    """Process a single decision for OpenSkill rating."""
    try:
        # Parse lawyer lists
        import json

        advogados_ativo = (
            json.loads(advogados_ativo_json) if advogados_ativo_json else []
        )
        advogados_passivo = (
            json.loads(advogados_passivo_json) if advogados_passivo_json else []
        )

        # Extract lawyer names (remove OAB info)
        def extract_lawyer_name(lawyer_str):
            # Remove OAB information like "(OAB/RO 1234)"
            import re

            name = re.sub(r"\s*\(OAB[^)]*\)\s*", "", lawyer_str).strip()
            return name.upper()  # Normalize to uppercase

        team_ativo = [
            extract_lawyer_name(adv) for adv in advogados_ativo if adv.strip()
        ]
        team_passivo = [
            extract_lawyer_name(adv) for adv in advogados_passivo if adv.strip()
        ]

        # Skip if no lawyers found
        if not team_ativo and not team_passivo:
            return False

        # Determine match result for OpenSkill
        if resultado.lower() in ["procedente", "procedente em parte"]:
            match_result = "win_a"  # Polo ativo wins
        elif resultado.lower() in ["improcedente"]:
            match_result = "win_b"  # Polo passivo wins
        elif resultado.lower() in ["acordo", "homologação de acordo"]:
            match_result = "draw"
        else:
            # Skip unknown results
            return False

        # Get or create ratings for lawyers
        from openskill_rating import create_rating, rate_teams

        def get_or_create_lawyer_rating(lawyer_name):
            # Check if lawyer exists in database
            existing = db.conn.execute(
                """
                SELECT mu, sigma FROM ratings WHERE advogado_id = ?
            """,
                [lawyer_name],
            ).fetchone()

            if existing:
                return create_rating(
                    os_model, mu=existing[0], sigma=existing[1], name=lawyer_name
                )
            else:
                # Create new rating with default values
                return create_rating(os_model, name=lawyer_name)

        # Build team ratings
        team_ativo_ratings = []
        for lawyer in team_ativo:
            if lawyer:  # Skip empty names
                rating = get_or_create_lawyer_rating(lawyer)
                team_ativo_ratings.append(rating)

        team_passivo_ratings = []
        for lawyer in team_passivo:
            if lawyer:  # Skip empty names
                rating = get_or_create_lawyer_rating(lawyer)
                team_passivo_ratings.append(rating)

        # Skip if no valid teams
        if not team_ativo_ratings and not team_passivo_ratings:
            return False

        # Handle single-team cases (add dummy opponent)
        if not team_ativo_ratings:
            team_ativo_ratings = [create_rating(os_model, name="DUMMY_ATIVO")]
        if not team_passivo_ratings:
            team_passivo_ratings = [create_rating(os_model, name="DUMMY_PASSIVO")]

        # Calculate new ratings
        new_team_ativo, new_team_passivo = rate_teams(
            os_model, team_ativo_ratings, team_passivo_ratings, match_result
        )

        # Update ratings in database
        for rating in new_team_ativo:
            if not rating.name.startswith("DUMMY_"):
                _update_lawyer_rating(rating.name, rating.mu, rating.sigma)

        for rating in new_team_passivo:
            if not rating.name.startswith("DUMMY_"):
                _update_lawyer_rating(rating.name, rating.mu, rating.sigma)

        # Store match record
        _store_match_record(
            decision_id, numero_processo, team_ativo, team_passivo, match_result
        )

        return True

    except Exception as e:
        typer.echo(f"⚠️  Error processing decision {numero_processo}: {e}")
        return False


def _update_lawyer_rating(lawyer_name: str, mu: float, sigma: float):
    """Update or insert lawyer rating in database."""
    # Check if lawyer exists
    existing = db.conn.execute(
        """
        SELECT total_partidas FROM ratings WHERE advogado_id = ?
    """,
        [lawyer_name],
    ).fetchone()

    if existing:
        # Update existing
        total_partidas = existing[0] + 1
        db.conn.execute(
            """
            UPDATE ratings 
            SET mu = ?, sigma = ?, total_partidas = ?, updated_at = CURRENT_TIMESTAMP
            WHERE advogado_id = ?
        """,
            [mu, sigma, total_partidas, lawyer_name],
        )
    else:
        # Insert new
        db.conn.execute(
            """
            INSERT INTO ratings (advogado_id, mu, sigma, total_partidas, created_at, updated_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
            [lawyer_name, mu, sigma],
        )


def _store_match_record(
    decision_id: int,
    numero_processo: str,
    team_ativo: List[str],
    team_passivo: List[str],
    resultado: str,
):
    """Store match record in partidas table."""
    try:
        db.conn.execute(
            """
            INSERT INTO partidas (
                decisao_id, numero_processo, advogados_polo_ativo, advogados_polo_passivo,
                resultado_partida, created_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            [
                decision_id,
                numero_processo,
                json.dumps(team_ativo),
                json.dumps(team_passivo),
                resultado,
            ],
        )
    except Exception as e:
        typer.echo(f"⚠️  Failed to store match record: {e}")


def _show_rating_stats():
    """Show current rating statistics."""
    try:
        # Top rated lawyers
        top_lawyers = db.conn.execute("""
            SELECT advogado_id, mu, sigma, total_partidas,
                   mu - 3 * sigma as conservative_skill
            FROM ratings 
            WHERE total_partidas >= 3
            ORDER BY conservative_skill DESC
            LIMIT 10
        """).fetchall()

        if top_lawyers:
            typer.echo("\n🏆 Top 10 Lawyers (by conservative skill):")
            for i, lawyer in enumerate(top_lawyers, 1):
                name = lawyer[0]
                mu = lawyer[1]
                sigma = lawyer[2]
                partidas = lawyer[3]
                conservative = lawyer[4]
                typer.echo(
                    f"{i:2d}. {name[:30]:<30} | Skill: {conservative:6.1f} | Games: {partidas:3d} | μ={mu:5.1f} σ={sigma:4.1f}"
                )

        # Overall stats
        total_lawyers = db.conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
        total_matches = db.conn.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]

        typer.echo("\n📊 Overall Statistics:")
        typer.echo(f"├── Total Lawyers: {total_lawyers:,}")
        typer.echo(f"└── Total Matches: {total_matches:,}")

    except Exception as e:
        typer.echo(f"⚠️  Failed to show statistics: {e}")


@app.command("get-urls")
def get_urls(
    date: Optional[str] = typer.Option(
        None, "--date", help="Date in YYYY-MM-DD format to collect"
    ),
    latest: bool = typer.Option(
        False, "--latest", help="Fetch the latest available PDF"
    ),
    tribunal: str = typer.Option(
        "tjro", "--tribunal", help="Tribunal to fetch from (tjro, tjsp, etc.)"
    ),
    to_queue: bool = typer.Option(
        False, "--to-queue", help="Add URLs to queue instead of downloading immediately"
    ),
    as_diario: bool = typer.Option(
        False, "--as-diario", help="Use new Diario dataclass interface"
    ),
    db_path: Path = typer.Option(
        Path("data/causaganha.duckdb"), "--db-path", help="Path to DuckDB database file"
    ),
):
    """Get URLs and download judicial diarios for specific dates or latest available."""
    # Setup logging
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d %(funcName)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validate tribunal
    if tribunal.lower() not in ["tjro"]:
        typer.echo(
            f"❌ Unsupported tribunal: {tribunal}. Currently supported: tjro", err=True
        )
        raise typer.Exit(1)

    if as_diario:
        # New Diario-based workflow
        _handle_diario_workflow(date, latest, tribunal, to_queue, db_path)
        return

    if to_queue:
        # Just get URLs and add to queue
        import datetime

        # Import appropriate tribunal-specific functions
        if tribunal.lower() == "tjro":
            from tribunais.tjro.downloader import get_tjro_pdf_url

        if not date and not latest:
            typer.echo(
                "📅 No date or --latest flag specified. Getting yesterday's diario URL."
            )

        # Get the URL(s) to queue
        urls_to_queue = []

        if latest:
            # For latest, we need to discover the most recent URL
            typer.echo(f"🔍 Finding latest {tribunal.upper()} diario URL...")
            # This would need implementation in downloader to get URL without downloading
            typer.echo("⚠️  Latest URL discovery not yet implemented for queue mode")
            return
        elif date:
            try:
                target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                url = get_tjro_pdf_url(target_date)
                if url:
                    urls_to_queue.append(url)
                else:
                    typer.echo(f"❌ No URL found for date {date}")
                    raise typer.Exit(1)
            except ValueError:
                typer.echo(f"❌ Invalid date format: '{date}'. Please use YYYY-MM-DD.")
                raise typer.Exit(1)
        else:
            # Default to yesterday
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            url = get_tjro_pdf_url(yesterday)
            if url:
                urls_to_queue.append(url)
            else:
                typer.echo(f"❌ No URL found for yesterday ({yesterday})")
                raise typer.Exit(1)

        # Add URLs to queue
        from urllib.parse import urlparse
        import json

        # Initialize job queue table if it doesn't exist (reuse from queue command)
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS job_queue (
                id INTEGER PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                date DATE,
                tribunal TEXT,
                filename TEXT,
                metadata JSON,
                status TEXT DEFAULT 'queued',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                ia_identifier TEXT,
                analyze_result JSON,
                arquivo_path TEXT,
                queue_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        queued_count = 0
        for url in urls_to_queue:
            if not validate_tribunal_url(url):
                typer.echo(f"❌ Only .jus.br domains are allowed: {url}", err=True)
                continue

            tribunal = extract_tribunal_from_url(url)
            date = extract_date_from_url(url)
            filename = Path(urlparse(url).path).name

            try:
                db.conn.execute(
                    """
                    INSERT INTO job_queue (url, date, tribunal, filename, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    [url, date, tribunal, filename, json.dumps({})],
                )
                queued_count += 1

            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    typer.echo(f"⚠️  URL already in queue: {url}")
                else:
                    typer.echo(f"❌ Error queuing {url}: {e}", err=True)

        typer.echo(f"✅ Added {queued_count} URL(s) to queue")

    else:
        # Download and archive immediately
        if not date and not latest:
            typer.echo(
                f"📅 No date or --latest flag specified. Getting yesterday's {tribunal.upper()} diario."
            )

        # Import appropriate tribunal-specific functions
        if tribunal.lower() == "tjro":
            from tribunais.tjro.collect_and_archive import collect_and_archive_diario

        with typer.progressbar(
            length=1, label=f"Getting {tribunal.upper()} diario"
        ) as progress:
            archive_url = collect_and_archive_diario(
                date=date, latest=latest, db_path=db_path
            )
            progress.update(1)

        if archive_url:
            typer.echo(f"✅ Successfully archived to: {archive_url}")
        else:
            typer.echo("❌ Failed to get and archive diario")
            raise typer.Exit(1)


@app.command()
def pipeline(
    from_csv: Optional[Path] = typer.Option(
        None, "--from-csv", help="CSV file with URLs"
    ),
    resume: bool = typer.Option(False, "--resume", help="Resume interrupted pipeline"),
    stages: Optional[str] = typer.Option(
        None, "--stages", help="Comma-separated stages to run"
    ),
    stop_on_error: bool = typer.Option(
        False, "--stop-on-error", help="Stop on first error"
    ),
    limit: Optional[int] = typer.Option(None, "--limit", help="Limit items per stage"),
):
    """Run full pipeline: queue → archive → analyze → score."""

    # Determine which stages to run
    all_stages = ["queue", "archive", "analyze", "score"]

    if stages:
        selected_stages = [s.strip() for s in stages.split(",")]
        # Validate stages
        invalid_stages = [s for s in selected_stages if s not in all_stages]
        if invalid_stages:
            typer.echo(
                f"❌ Invalid stages: {invalid_stages}. Valid stages: {all_stages}",
                err=True,
            )
            raise typer.Exit(1)
        pipeline_stages = selected_stages
    else:
        pipeline_stages = all_stages

    # If not resuming and no CSV provided, check if we need to queue first
    if not resume and not from_csv and "queue" in pipeline_stages:
        typer.echo(
            "❌ Either --from-csv or --resume is required for pipeline", err=True
        )
        raise typer.Exit(1)

    # Validate configuration for stages that need it
    if "analyze" in pipeline_stages:
        from extractor import GeminiExtractor

        extractor = GeminiExtractor()
        if not extractor.gemini_configured:
            typer.echo(
                "❌ Gemini not configured for analyze stage. Please set GEMINI_API_KEY environment variable."
            )
            typer.echo(
                "💡 Get your API key from: https://aistudio.google.com/app/apikey"
            )
            raise typer.Exit(1)

    typer.echo(f"🚀 Starting pipeline with stages: {' → '.join(pipeline_stages)}")

    try:
        # Stage 1: Queue (only if CSV provided)
        if "queue" in pipeline_stages and from_csv:
            typer.echo("\n📝 Stage 1: Queuing URLs...")
            result = _run_stage(lambda: queue(from_csv=from_csv), stop_on_error)
            if not result:
                return

        # Stage 2: Archive
        if "archive" in pipeline_stages:
            typer.echo("\n📦 Stage 2: Archiving documents...")
            result = _run_stage(lambda: archive(limit=limit), stop_on_error)
            if not result:
                return

        # Stage 3: Analyze
        if "analyze" in pipeline_stages:
            typer.echo("\n🔍 Stage 3: Analyzing documents...")
            result = _run_stage(lambda: analyze(limit=limit), stop_on_error)
            if not result:
                return

        # Stage 4: Score
        if "score" in pipeline_stages:
            typer.echo("\n⭐ Stage 4: Calculating ratings...")
            result = _run_stage(lambda: score(), stop_on_error)
            if not result:
                return

        typer.echo("\n✅ Pipeline completed successfully!")

        # Show final statistics
        typer.echo("\n📊 Final Pipeline Status:")
        stats()

    except KeyboardInterrupt:
        typer.echo("\n⚠️  Pipeline interrupted by user")
        typer.echo("💡 Use --resume to continue from where you left off")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"\n❌ Pipeline failed: {e}")
        raise typer.Exit(1)


def _run_stage(stage_func, stop_on_error: bool) -> bool:
    """Run a pipeline stage with error handling."""
    try:
        stage_func()
        return True
    except Exception as e:
        typer.echo(f"❌ Stage failed: {e}")
        if stop_on_error:
            typer.echo("⛔ Stopping pipeline due to --stop-on-error flag")
            return False
        else:
            typer.echo("⚠️  Continuing with next stage...")
            return True


@app.command()
def stats():
    """Show processing statistics and pipeline progress."""
    # Check if job_queue table exists
    try:
        result = db.conn.execute("""
            SELECT status, COUNT(*) as count
            FROM job_queue
            GROUP BY status
            ORDER BY status
        """).fetchall()

        if not result:
            typer.echo("📊 No jobs in queue yet")
            return

        typer.echo("📊 Pipeline Status:")
        status_counts = dict(result)

        for status in ["queued", "archived", "analyzed", "scored", "failed"]:
            count = status_counts.get(status, 0)
            status_icon = {
                "queued": "⏳",
                "archived": "📦",
                "analyzed": "🔍",
                "scored": "⭐",
                "failed": "❌",
            }[status]
            typer.echo(f"├── {status_icon} {status.title()}: {count:,} items")

        # Total
        total = sum(status_counts.values())
        typer.echo(f"└── 📈 Total: {total:,} items")

    except Exception as e:
        if "no such table" in str(e):
            typer.echo("📊 No jobs queued yet - use 'causaganha queue' first")
        else:
            typer.echo(f"❌ Error getting stats: {e}", err=True)


@app.command()
def config():
    """Show current configuration."""
    typer.echo("⚙️  Current Configuration:")
    typer.echo(f"├── Database: {config['database']['path']}")
    typer.echo(f"├── OpenSkill μ: {config['openskill']['mu']}")
    typer.echo(f"├── OpenSkill σ: {config['openskill']['sigma']}")
    typer.echo(f"└── OpenSkill β: {config['openskill']['beta']}")


def _handle_diario_workflow(
    date: Optional[str], latest: bool, tribunal: str, to_queue: bool, db_path: Path
) -> None:
    """Handle the new Diario-based workflow."""
    import datetime
    from models.diario import Diario
    from tribunais import get_adapter, is_tribunal_supported
    from database import CausaGanhaDB

    # Validate tribunal support in new system
    if not is_tribunal_supported(tribunal):
        typer.echo(
            f"❌ Tribunal '{tribunal}' not supported in Diario system yet", err=True
        )
        raise typer.Exit(1)

    # Get tribunal adapter
    adapter = get_adapter(tribunal)

    # Create diario object
    diario = None

    if latest:
        typer.echo(f"🔍 Finding latest {tribunal.upper()} diario...")
        url = adapter.discovery.get_latest_diario_url()
        if url:
            # Extract date from URL or use today
            today = datetime.date.today()
            diario = Diario(
                tribunal=tribunal,
                data=today,
                url=url,
                filename=Path(url).name if url else None,
            )
        else:
            typer.echo(f"❌ No latest diario found for {tribunal.upper()}")
            raise typer.Exit(1)

    elif date:
        try:
            target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            typer.echo(f"🔍 Finding {tribunal.upper()} diario for {target_date}...")
            diario = adapter.create_diario(target_date)
            if not diario:
                typer.echo(f"❌ No diario found for {target_date}")
                raise typer.Exit(1)
        except ValueError:
            typer.echo(f"❌ Invalid date format: '{date}'. Please use YYYY-MM-DD.")
            raise typer.Exit(1)
    else:
        # Default to yesterday
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        typer.echo(
            f"📅 No date specified. Getting {tribunal.upper()} diario for yesterday ({yesterday})"
        )
        diario = adapter.create_diario(yesterday)
        if not diario:
            typer.echo(f"❌ No diario found for yesterday ({yesterday})")
            raise typer.Exit(1)

    # Add discovered metadata
    if hasattr(adapter.discovery, "get_diario_metadata"):
        diario.metadata.update(adapter.discovery.get_diario_metadata(diario.url))

    if to_queue:
        # Add to queue using new Diario system
        with CausaGanhaDB(db_path) as db:
            success = db.queue_diario(diario)
            if success:
                typer.echo(
                    f"✅ Added {diario.display_name} to queue using Diario system"
                )
            else:
                typer.echo(f"❌ Failed to queue {diario.display_name}")
                raise typer.Exit(1)
    else:
        # Process immediately using new Diario system
        typer.echo(f"🚀 Processing {diario.display_name} immediately...")

        with typer.progressbar(
            length=3, label=f"Processing {tribunal.upper()} diario"
        ) as progress:
            try:
                # Download
                typer.echo(f"⬇️  Downloading {diario.display_name}...")
                diario = adapter.downloader.download_diario(diario)
                progress.update(1)

                if diario.status == "downloaded":
                    # Archive
                    typer.echo(f"📁 Archiving {diario.display_name}...")
                    diario = adapter.downloader.archive_to_ia(diario)
                    progress.update(1)

                    if diario.ia_identifier:
                        # Analyze
                        typer.echo(f"🔍 Analyzing {diario.display_name}...")
                        diario = adapter.analyzer.analyze_diario(diario)
                        progress.update(1)

                        # Update database with final status
                        with CausaGanhaDB(db_path) as db:
                            db.queue_diario(diario)

                        # Show results
                        decision_count = diario.metadata.get("decision_count", 0)
                        ia_url = diario.metadata.get("ia_url", "Unknown")

                        typer.echo(f"✅ Successfully processed {diario.display_name}")
                        typer.echo(f"📊 Extracted {decision_count} decisions")
                        typer.echo(f"🌐 Archived at: {ia_url}")

                        if "tjro_analysis" in diario.metadata:
                            stats = diario.metadata["tjro_analysis"]
                            typer.echo(
                                f"📈 Unique processes: {stats['unique_processes']}"
                            )
                            typer.echo(
                                f"👥 Lawyers: {stats['lawyer_count']['ativo']} active, {stats['lawyer_count']['passivo']} passive"
                            )
                    else:
                        typer.echo(f"⚠️  Archive failed for {diario.display_name}")
                        progress.update(2)
                else:
                    typer.echo(f"❌ Download failed for {diario.display_name}")
                    progress.update(3)
                    raise typer.Exit(1)

            except Exception as e:
                typer.echo(f"❌ Error processing {diario.display_name}: {e}")
                raise typer.Exit(1)


@app.command("diario")
def diario_cmd(
    action: str = typer.Argument(..., help="Action: list, stats, process"),
    tribunal: Optional[str] = typer.Option(
        None, "--tribunal", help="Filter by tribunal"
    ),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Limit results"),
    db_path: Path = typer.Option(Path("data/causaganha.duckdb"), "--db-path"),
):
    """Manage diarios using the new Diario dataclass system."""
    from database import CausaGanhaDB
    from tribunais import list_supported_tribunals

    if action == "stats":
        with CausaGanhaDB(db_path) as db:
            stats = db.get_diario_statistics()

            typer.echo("📊 Diario Statistics")
            typer.echo("=" * 50)
            typer.echo(f"Total Diarios: {stats.get('total_diarios', 0)}")
            typer.echo(f"Recent Activity (7 days): {stats.get('recent_activity', 0)}")

            typer.echo("\n📈 By Status:")
            for status, count in stats.get("by_status", {}).items():
                typer.echo(f"  {status}: {count}")

            typer.echo("\n🏛️  By Tribunal:")
            for tribunal, count in stats.get("by_tribunal", {}).items():
                typer.echo(f"  {tribunal.upper()}: {count}")

            typer.echo(
                f"\n🔧 Supported Tribunals: {', '.join(list_supported_tribunals())}"
            )

    elif action == "list":
        with CausaGanhaDB(db_path) as db:
            if status:
                diarios = db.get_diarios_by_status(status)
                typer.echo(f"📋 Diarios with status '{status}':")
            elif tribunal:
                diarios = db.get_diarios_by_tribunal(tribunal)
                typer.echo(f"📋 Diarios for tribunal '{tribunal.upper()}':")
            else:
                # Get all by getting each status
                diarios = []
                for st in ["pending", "downloaded", "analyzed", "scored"]:
                    diarios.extend(db.get_diarios_by_status(st))
                typer.echo("📋 All Diarios:")

            if limit:
                diarios = diarios[:limit]

            if not diarios:
                typer.echo("No diarios found.")
            else:
                typer.echo(f"Found {len(diarios)} diario(s):")
                for diario in diarios:
                    metadata_info = ""
                    if "decision_count" in diario.metadata:
                        metadata_info = (
                            f" ({diario.metadata['decision_count']} decisions)"
                        )

                    typer.echo(
                        f"  • {diario.display_name} - {diario.status}{metadata_info}"
                    )

    elif action == "process":
        if not tribunal:
            typer.echo("❌ --tribunal is required for process action")
            raise typer.Exit(1)

        with CausaGanhaDB(db_path) as db:
            pending_diarios = db.get_diarios_by_status("pending")
            tribunal_diarios = [d for d in pending_diarios if d.tribunal == tribunal]

            if not tribunal_diarios:
                typer.echo(f"No pending diarios found for {tribunal.upper()}")
                return

            typer.echo(
                f"🚀 Processing {len(tribunal_diarios)} pending {tribunal.upper()} diarios..."
            )

            from tribunais import get_adapter

            adapter = get_adapter(tribunal)

            for diario in tribunal_diarios:
                try:
                    typer.echo(f"Processing {diario.display_name}...")

                    # Process the diario
                    processed_diario = adapter.process_diario(diario)

                    # Update database
                    db.queue_diario(processed_diario)

                    typer.echo(f"✅ Completed {diario.display_name}")

                except Exception as e:
                    typer.echo(f"❌ Failed {diario.display_name}: {e}")

    else:
        typer.echo(f"❌ Unknown action: {action}")
        typer.echo("Available actions: list, stats, process")
        raise typer.Exit(1)


@app.command("db")
def database_cmd(
    action: str = typer.Argument(
        ..., help="Action to perform: migrate, status, sync, backup, reset"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force operation without confirmation"
    ),
):
    """Database management operations."""

    if action == "migrate":
        _db_migrate()
    elif action == "status":
        _db_status()
    elif action == "sync":
        _db_sync(force)
    elif action == "backup":
        _db_backup()
    elif action == "reset":
        _db_reset(force)
    else:
        typer.echo(f"❌ Unknown action: {action}")
        typer.echo("Valid actions: migrate, status, sync, backup, reset")
        raise typer.Exit(1)


def _db_migrate():
    """Run database migrations."""
    try:
        from migration_runner import run_migrations

        typer.echo("🔄 Running database migrations...")
        run_migrations()
        typer.echo("✅ Database migrations completed")
    except ImportError:
        typer.echo("❌ Migration runner not found")
    except Exception as e:
        typer.echo(f"❌ Migration failed: {e}")


def _db_status():
    """Show database status and statistics."""
    try:
        db_path = Path(config["database"]["path"])

        typer.echo("💾 Database Status:")
        typer.echo(f"├── Path: {db_path}")
        typer.echo(f"├── Exists: {'✅' if db_path.exists() else '❌'}")

        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            typer.echo(f"├── Size: {size_mb:.1f} MB")

            # Table counts
            tables_info = [
                ("job_queue", "Job Queue"),
                ("ratings", "Lawyer Ratings"),
                ("partidas", "Matches"),
                ("decisoes", "Decisions"),
                ("json_files", "JSON Files"),
            ]

            typer.echo("├── Table Counts:")
            for table, label in tables_info:
                try:
                    count = db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[
                        0
                    ]
                    typer.echo(f"│   ├── {label}: {count:,}")
                except Exception:
                    typer.echo(f"│   ├── {label}: N/A")

            # Queue status
            try:
                queue_stats = db.conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM job_queue 
                    GROUP BY status
                """).fetchall()

                if queue_stats:
                    typer.echo("└── Queue Status:")
                    for status, count in queue_stats:
                        typer.echo(f"    ├── {status}: {count:,}")
                else:
                    typer.echo("└── Queue Status: Empty")
            except Exception:
                typer.echo("└── Queue Status: N/A")

    except Exception as e:
        typer.echo(f"❌ Failed to get database status: {e}")


def _db_sync(force: bool):
    """Sync database with Internet Archive."""
    try:
        from ia_database_sync import main as sync_main
        import sys

        typer.echo("🔄 Syncing database with Internet Archive...")

        # Set up sys.argv for ia_database_sync
        old_argv = sys.argv
        sys.argv = ["ia_database_sync.py", "sync"]
        if force:
            sys.argv.append("--force")

        try:
            sync_main()
            typer.echo("✅ Database sync completed")
        finally:
            sys.argv = old_argv

    except ImportError:
        typer.echo("❌ IA database sync module not found")
    except Exception as e:
        typer.echo(f"❌ Database sync failed: {e}")


def _db_backup():
    """Create database backup."""
    try:
        db_path = Path(config["database"]["path"])
        if not db_path.exists():
            typer.echo("❌ Database file not found")
            return

        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}.duckdb"

        import shutil

        shutil.copy2(db_path, backup_path)

        size_mb = backup_path.stat().st_size / (1024 * 1024)
        typer.echo(f"✅ Database backup created: {backup_path.name} ({size_mb:.1f} MB)")

    except Exception as e:
        typer.echo(f"❌ Backup failed: {e}")


def _db_reset(force: bool):
    """Reset database (dangerous operation)."""
    db_path = Path(config["database"]["path"])

    if not force:
        confirm = typer.confirm(
            f"⚠️  This will DELETE the entire database at {db_path}\n"
            "Are you sure you want to continue?"
        )
        if not confirm:
            typer.echo("❌ Database reset cancelled")
            return

    try:
        if db_path.exists():
            db_path.unlink()
            typer.echo("🗑️  Database file deleted")

        # Reinitialize database
        _db_migrate()
        typer.echo("✅ Database reset completed")

    except Exception as e:
        typer.echo(f"❌ Database reset failed: {e}")


if __name__ == "__main__":
    app()
