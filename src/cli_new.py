"""CausaGanha CLI - Modern command-line interface for judicial document processing."""

import typer
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import csv
from urllib.parse import urlparse
import re
from datetime import datetime, date as DateObject
import json
import asyncio
import aiohttp
import hashlib
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
import time
import logging
from tqdm.asyncio import tqdm as asyncio_tqdm  # For async usage
from tqdm import tqdm  # For sync usage if needed elsewhere

from database import CausaGanhaDB
from config import load_config
from extractor import GeminiExtractor
from ia_helpers import (
    archive_diario_to_master_item,
    update_ia_file_level_metadata_summary,
    download_ia_file_async,
    MASTER_IA_ITEM_ID,
)

app = typer.Typer(
    name="causaganha",
    help="Judicial document processing pipeline with OpenSkill rating system.",
    no_args_is_help=True,
)

config_data = load_config()
db = CausaGanhaDB(Path(config_data["database"]["path"]))
_LOG_ = logging.getLogger(__name__)


def _setup_logging():
    log_level_str = config_data.get("logging", {}).get("level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


_setup_logging()


# --- Utility Functions ---
def extract_tribunal_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def validate_tribunal_url(url: str) -> bool:
    return urlparse(url).netloc.lower().endswith(".jus.br")


def extract_date_from_url(url: str) -> Optional[str]:
    # (Implementation as before)
    date_patterns = [
        r"diario(\d{8})",
        r"(\d{8})",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}-\d{2}-\d{4})",
    ]
    for p in date_patterns:
        m = re.search(p, url)
        if m:
            ds = m.group(1)
            try:
                if len(ds) == 8 and ds.isdigit():
                    return datetime.strptime(ds, "%Y%m%d").strftime("%Y-%m-%d")
                elif "-" in ds:
                    pts = ds.split("-")
                    if len(pts[0]) == 4:
                        return datetime.strptime(ds, "%Y-%m-%d").strftime("%Y-%m-%d")
                    else:
                        return datetime.strptime(ds, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


# --- CLI Commands ---
@app.command()
def queue(
    url: Optional[str] = typer.Option(None, "--url"),
    from_csv: Optional[Path] = typer.Option(None, "--from-csv"),
):
    if not url and not from_csv:
        typer.echo("❌ --url or --from-csv required.", err=True)
        _LOG_.error("Q:No input")
        raise typer.Exit(1)
    if url and from_csv:
        typer.echo("❌ Cannot use both.", err=True)
        _LOG_.error("Q:Both inputs")
        raise typer.Exit(1)
    db.conn.execute(
        "CREATE TABLE IF NOT EXISTS job_queue (id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, date DATE, tribunal TEXT, filename TEXT, metadata JSON, status TEXT DEFAULT 'queued', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, error_message TEXT, retry_count INTEGER DEFAULT 0, ia_identifier TEXT, ia_remote_filename TEXT, analyze_result JSON, score_updated BOOLEAN DEFAULT FALSE, ia_metadata_synced BOOLEAN DEFAULT FALSE)"
    )
    ul: List[Dict[str, Any]] = []
    if url:
        if not validate_tribunal_url(url):
            typer.echo(f"❌ Invalid URL:{url}", err=True)
            _LOG_.error(f"Q:Invalid URL {url}")
            raise typer.Exit(1)
        ul.append(
            {
                "url": url,
                "date_str": extract_date_from_url(url),
                "tribunal_code": extract_tribunal_from_url(url),
                "original_filename": Path(urlparse(url).path).name,
            }
        )
    elif from_csv:
        if not from_csv.exists():
            typer.echo(f"❌ CSV missing:{from_csv}", err=True)
            _LOG_.error(f"Q:CSV missing {from_csv}")
            raise typer.Exit(1)
        with open(from_csv, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            if "url" not in r.fieldnames:
                typer.echo("❌ CSV needs 'url' col.", err=True)
                _LOG_.error("Q:CSV no 'url'")
                raise typer.Exit(1)
            for rn, row in enumerate(r, 1):
                curl = row["url"].strip()
                if not curl:
                    continue
                if not validate_tribunal_url(curl):
                    _LOG_.warning(f"Q:Skip CSV URL(row {rn}):{curl}")
                    continue
                ul.append(
                    {
                        "url": curl,
                        "date_str": row.get("date", "").strip()
                        or extract_date_from_url(curl),
                        "tribunal_code": row.get("tribunal", "").strip()
                        or extract_tribunal_from_url(curl),
                        "original_filename": row.get("filename", "").strip()
                        or Path(urlparse(curl).path).name,
                    }
                )
    q_ok, q_skip = 0, 0
    for item in ul:
        try:
            imeta = {"source": "cli_queue", "orig_fname": item["original_filename"]}
            db.conn.execute(
                "INSERT INTO job_queue(url, date, tribunal, filename, metadata, status) VALUES(?,?,?,?,?,'queued')",
                [
                    item["url"],
                    item["date_str"],
                    item["tribunal_code"],
                    item["original_filename"],
                    json.dumps(imeta),
                ],
            )
            q_ok += 1
            _LOG_.info(f"Queued:{item['url']}")
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                q_skip += 1
                _LOG_.info(f"Skip duplicate:{item['url']}")
            else:
                typer.echo(f"❌ Q Error {item['url']}:{e}", err=True)
                _LOG_.error(f"Q Error {item['url']}:{e}")
    typer.echo(f"✅ Queued {q_ok} new.")
    if q_skip > 0:
        typer.echo(f"ℹ️ Skipped {q_skip} (exists).")


@app.command("get-urls")
def get_urls(
    date: Optional[str] = typer.Option(None, help="Date YYYY-MM-DD."),
    latest: bool = typer.Option(False, help="Fetch latest."),
    tribunal: str = typer.Option("tjro", help="Tribunal code."),
    to_queue: bool = typer.Option(
        True, "--to-queue/--no-to-queue", help="Queue or process now."
    ),
):
    docs: List[Dict[str, Any]] = []
    if tribunal.lower() == "tjro":
        from tribunais.tjro.downloader import (
            get_tjro_pdf_url,
            get_latest_tjro_url_and_date,
        )

        url_v: Optional[str] = None
        date_v: Optional[DateObject] = None
        if latest:
            _LOG_.info(f"Latest {tribunal.upper()}...")
            url_v, date_v = get_latest_tjro_url_and_date()
        elif date:
            try:
                date_v = datetime.strptime(date, "%Y-%m-%d").date()
                _LOG_.info(f"For {tribunal.upper()} {date_v}...")
            except ValueError:
                _LOG_.error(f"Invalid date:{date}.")
                typer.echo(f"❌ Invalid date:{date}.", err=True)
                raise typer.Exit(1)
            url_v = get_tjro_pdf_url(date_v)
            if not url_v:
                _LOG_.error(f"No URL for {tribunal.upper()} on {date}.")
                typer.echo(f"❌ No URL for {date}.", err=True)
                raise typer.Exit(1)
        else:
            _LOG_.error("Date or latest needed.")
            typer.echo("❌ --date or --latest required.", err=True)
            raise typer.Exit(1)
        if url_v and date_v:
            if not validate_tribunal_url(url_v):
                _LOG_.error(f"Invalid URL {url_v}.")
                typer.echo(f"❌ Invalid URL:{url_v}", err=True)
                raise typer.Exit(1)
            docs.append(
                {
                    "url": url_v,
                    "date_obj": date_v,
                    "tribunal_code": tribunal.lower(),
                    "original_filename": Path(urlparse(url_v).path).name,
                }
            )
    else:
        _LOG_.error(f"Discovery for {tribunal} N/A.")
        typer.echo(f"❌ Discovery for {tribunal} N/A.", err=True)
        raise typer.Exit(1)
    if not docs:
        _LOG_.info("No docs by get-urls.")
        typer.echo("ℹ️ No docs found.")
        return
    for dinfo in docs:
        durl, dobj, tcode, ofname = (
            dinfo["url"],
            dinfo["date_obj"],
            dinfo["tribunal_code"],
            dinfo["original_filename"],
        )
        dstr = dobj.strftime("%Y-%m-%d")
        dispname = f"{tcode.upper()} {dstr} ({ofname})"
        if to_queue:
            try:
                db.conn.execute(
                    "INSERT INTO job_queue(url, date, tribunal, filename, metadata, status) VALUES(?,?,?,?,?,'queued') ON CONFLICT(url) DO NOTHING",
                    [
                        durl,
                        dstr,
                        tcode,
                        ofname,
                        json.dumps({"source": "get-urls --to-queue"}),
                    ],
                )
                if db.conn.changes() > 0:
                    typer.echo(f"✅ Queued:{dispname}")
                    _LOG_.info(f"Queued(get-urls):{dispname}")
                else:
                    typer.echo(f"ℹ️ Exists:{durl}")
                    _LOG_.info(f"Exists(get-urls):{durl}")
            except Exception as e:
                typer.echo(f"❌ Q Error {dispname}:{e}", err=True)
                _LOG_.error(f"Q Error(get-urls)for {dispname}:{e}")
        else:
            _LOG_.info(f"Immediate proc(get-urls):{dispname}")
            typer.echo(f"🚀 Processing now:{dispname}")
            with tempfile.TemporaryDirectory(prefix="cg_imm_") as tmp_dn:
                tmp_d = Path(tmp_dn)
                lp: Optional[Path] = None
                try:

                    async def _dl():
                        async with (
                            aiohttp.ClientSession() as sess,
                            sess.get(durl) as rsp,
                        ):
                            rsp.raise_for_status()
                            cnt = await rsp.read()
                            if not cnt.startswith(b"%PDF"):
                                raise ValueError("Not PDF.")
                            sfn = "".join(
                                c if c.isalnum() or c in ("_", "-") else "_"
                                for c in Path(ofname).stem
                            )
                            sf = f"{sfn}.pdf"
                            dlp = tmp_d / sf
                            dlp.write_bytes(cnt)
                            _LOG_.info(f"DL OK:{dlp.name}")
                            return dlp

                    lp = asyncio.run(_dl())
                    if not (lp and lp.exists()):
                        raise Exception("DL Fail.")
                    ia_rf = f"{tcode}_{dstr}_{Path(ofname).stem.replace('.', '_')}.pdf"
                    mid, rip = asyncio.run(
                        archive_diario_to_master_item(lp, tcode, ia_rf)
                    )
                    if not (mid and rip):
                        raise Exception("IA Fail.")
                    _LOG_.info(f"IA OK:{mid}/{rip}")
                    imeta = {
                        "original_url": durl,
                        "publication_date": dstr,
                        "tribunal": tcode,
                    }
                    db.conn.execute(
                        "INSERT INTO job_queue(url, date, tribunal, filename, metadata, status, ia_identifier, ia_remote_filename, ia_metadata_synced) VALUES(?,?,?,?,?,?,?,?,FALSE) ON CONFLICT(url) DO UPDATE SET status='archived', date=excluded.date, tribunal=excluded.tribunal, filename=excluded.filename, metadata=excluded.metadata, ia_identifier=excluded.ia_identifier, ia_remote_filename=excluded.ia_remote_filename, ia_metadata_synced=FALSE, updated_at=CURRENT_TIMESTAMP",
                        [durl, dstr, tcode, ofname, json.dumps(imeta), mid, rip],
                    )
                    _LOG_.info(f"DB OK for {dispname}.")
                    typer.echo(f"   ✅ OK:{dispname}")
                except Exception as e:
                    typer.echo(f"   ❌ FAIL {dispname}:{e}", err=True)
                    _LOG_.error(f"Immediate FAIL {dispname}:{e}")
                    try:
                        db.conn.execute(
                            "INSERT INTO job_queue(url, date, tribunal, filename, metadata, status, error_message) VALUES(?,?,?,?,?,'failed',?) ON CONFLICT(url) DO UPDATE SET status='failed', error_message=excluded.error_message",
                            [
                                durl,
                                dstr,
                                tcode,
                                ofname,
                                json.dumps({}),
                                f"Immediate proc fail:{e}",
                            ],
                        )
                    except Exception as dbe:
                        typer.echo(f"   ❌ DB Log Fail:{dbe}", err=True)
                        _LOG_.error(f"DB log fail {dispname}:{dbe}")


# --- Archive Stage Logic ---
async def archive_stage_logic(
    limit: Optional[int] = None, max_concurrent_downloads: int = 3
):
    _LOG_.info(f"Archive Stage(lim={limit},concur={max_concurrent_downloads})")
    q = "SELECT id, url, tribunal, filename, date FROM job_queue WHERE status='queued' OR status='failed_download' ORDER BY CASE status WHEN 'failed_download' THEN 0 ELSE 1 END, retry_count ASC, created_at ASC"
    if limit:
        q += f" LIMIT {limit}"
    items = db.conn.execute(q).fetchall()
    if not items:
        _LOG_.info("Archive:No items.")
        typer.echo("📦 No items for archive.")
        return 0, 0
    _LOG_.info(f"Archive:Found {len(items)}.")
    typer.echo(f"📦 Archiving {len(items)} items...")
    ok, nok = 0, 0
    sem = asyncio.Semaphore(max_concurrent_downloads)

    async def _proc(jid, url, trib, fname, date_s):
        nonlocal ok, nok
        _LOG_.info(f"Archiving job {jid},{url}")
        sfn_stem = (
            "".join(
                c if c.isalnum() or c in ("_", "-") else "_" for c in Path(fname).stem
            )
            if fname
            else "diario"
        )
        with tempfile.TemporaryDirectory(prefix=f"cg_arch_{jid}_") as tmp_d_str:
            dl_d = Path(tmp_d_str)
            lp: Optional[Path] = None
            try:
                async with sem, aiohttp.ClientSession() as sess, sess.get(url) as r:
                    r.raise_for_status()
                    cont = await r.read()
                    if not cont.startswith(b"%PDF"):
                        raise ValueError("Not PDF.")
                    dl_f = f"{sfn_stem}.pdf"
                    lp = dl_d / dl_f
                    lp.write_bytes(cont)
                if not (lp and lp.exists()):
                    raise Exception("DL Fail.")
                eff_d = date_s if date_s else datetime.now().strftime("%Y-%m-%d")
                ia_rn = f"{trib}_{eff_d}_{sfn_stem}.pdf"
                mid, rip = await archive_diario_to_master_item(lp, trib, ia_rn)
                if mid and rip:
                    db.conn.execute(
                        "UPDATE job_queue SET status='archived', ia_identifier=?, ia_remote_filename=?, updated_at=CURRENT_TIMESTAMP, error_message=NULL, retry_count=0 WHERE id=?",
                        [mid, rip, jid],
                    )
                    ok += 1
                    _LOG_.info(f"OK job {jid} to IA:{mid}/{rip}")
                    typer.echo(f"   ✅ Archived:{url}->{mid}/{rip}")
                else:
                    raise Exception("IA Upload Fail.")
            except Exception as e:
                nok += 1
                _LOG_.error(f"FAIL job {jid}({url}):{e}")
                db.conn.execute(
                    "UPDATE job_queue SET status='failed_download', error_message=?, retry_count=retry_count+1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    [f"Archive stage:{type(e).__name__}-{e}", jid],
                )
                typer.echo(f"   ❌ Failed:{url}-{e}", err=True)

    if items:
        tasks = [_proc(j, u, t, fn, dt) for j, u, t, fn, dt in items]

        async def run_tasks_with_progress():
            await asyncio_tqdm.gather(*tasks, desc="Archiving items")

        asyncio.run(run_tasks_with_progress())

    typer.echo(f"--- Archive Summary:{ok} archived,{nok} failed.---")
    _LOG_.info(f"Archive Summary:{ok} ok,{nok} nok.")
    return ok, nok


# --- Analyze Stage Logic (Refactored with _populate_decisoes_from_analysis_result) ---
def _populate_decisoes_from_analysis_result(
    job_id: int, analysis_result: Dict[str, Any], original_filename_for_json_source: str
):
    """Helper to populate `decisoes` table from `analyze_result` data."""
    _LOG_.debug(
        f"Populating 'decisoes' table for job_id {job_id} from analysis_result."
    )
    decisions_to_store = []
    if isinstance(analysis_result, list):
        decisions_to_store = analysis_result
    elif isinstance(analysis_result, dict) and "decisions" in analysis_result:
        decisions_to_store = analysis_result.get("decisions", [])
    elif isinstance(analysis_result, dict) and "numero_processo" in analysis_result:
        decisions_to_store = [analysis_result]

    source_json_file_name = f"job_{job_id}_{original_filename_for_json_source}.json"

    for decision_data in decisions_to_store:
        if isinstance(decision_data, dict) and decision_data.get("numero_processo"):
            try:
                db.conn.execute(
                    """
                    INSERT OR REPLACE INTO decisoes (
                        numero_processo, json_source_file, tipo_decisao, resultado,
                        polo_ativo, polo_passivo, advogados_polo_ativo, advogados_polo_passivo,
                        resumo, raw_json_data, processed_for_openskill, validation_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE, 'pending', CURRENT_TIMESTAMP)
                """,
                    [
                        decision_data.get("numero_processo"),
                        source_json_file_name,
                        decision_data.get("tipo_decisao"),
                        decision_data.get("resultado"),
                        json.dumps(
                            decision_data.get("partes", {}).get("requerente", [])
                        ),
                        json.dumps(
                            decision_data.get("partes", {}).get("requerido", [])
                        ),
                        json.dumps(
                            decision_data.get("advogados", {}).get("requerente", [])
                        ),
                        json.dumps(
                            decision_data.get("advogados", {}).get("requerido", [])
                        ),
                        decision_data.get("resumo"),
                        json.dumps(decision_data),
                    ],
                )
                _LOG_.debug(
                    f"Stored decision {decision_data.get('numero_processo')} for job {job_id} in 'decisoes'."
                )
            except Exception as e:
                _LOG_.error(
                    f"Failed to store decision {decision_data.get('numero_processo')} (job {job_id}) into 'decisoes': {e}"
                )
        else:
            _LOG_.warning(
                f"Skipping invalid decision data for job {job_id}: {decision_data}"
            )


async def analyze_stage_logic(
    limit: Optional[int] = None,
    force_analysis: bool = False,
    max_concurrent_analyses: int = 2,
):
    _LOG_.info(
        f"Analyze Stage(lim={limit},force={force_analysis},concur={max_concurrent_analyses})"
    )
    s_cond = ["status='archived'"]
    if force_analysis:
        s_cond.extend(
            [
                "status='analyzed'",
                "status='ia_metadata_updated'",
                "status='failed_analysis'",
                "status='failed_metadata_sync'",
            ]
        )

    q = f"""SELECT id, url, ia_identifier, ia_remote_filename, analyze_result, tribunal, filename, date
            FROM job_queue
            WHERE ({" OR ".join(s_cond)})
              AND (ia_metadata_synced = FALSE OR ? = TRUE)
              AND ia_identifier = ?
              AND ia_remote_filename IS NOT NULL
            ORDER BY CASE status
                         WHEN 'archived' THEN 0
                         ELSE 1
                     END,
                     ia_metadata_synced ASC,
                     updated_at ASC"""
    if limit:
        q += f" LIMIT {limit}"
    items = db.conn.execute(q, [force_analysis, MASTER_IA_ITEM_ID]).fetchall()
    if not items:
        _LOG_.info("Analyze:No items.")
        typer.echo("🔍 No items for analysis/meta update.")
        return 0, 0, 0, 0
    _LOG_.info(f"Analyze:Found {len(items)}.")
    typer.echo(f"🔍 Processing {len(items)} items...")
    xtr = GeminiExtractor()
    llm_ok, meta_ok, nok, dec_stored_count = 0, 0, 0, 0
    sem = asyncio.Semaphore(max_concurrent_analyses)

    async def _proc(jid, iurl, mid, rf, an_s, tc, ofn, idt_s):
        nonlocal llm_ok, meta_ok, nok, dec_stored_count
        ana_data: Optional[Dict] = None
        _LOG_.info(f"Analyzing job {jid}:{rf}")
        typer.echo(f"--- Analyzing item ID {jid}:{rf} ---")
        if an_s:
            try:
                ana_data = json.loads(an_s)
            except json.JSONDecodeError:
                _LOG_.warning(f"Corrupt JSON job {jid}, re-analyze.")
        need_llm = force_analysis or not ana_data
        if need_llm:
            if not xtr.gemini_configured:
                _LOG_.error(f"Gemini N/A for job {jid}.LLM skip.")
                if not ana_data:
                    nok += 1
                    db.conn.execute(
                        "UPDATE job_queue SET status='failed_analysis',error_message='Gemini N/A'WHERE id=?",
                        [jid],
                    )
                    return
            else:
                _LOG_.debug(f"LLM for job {jid}")
                with tempfile.TemporaryDirectory(prefix=f"cg_an_{jid}_") as tmp_d_s:
                    tmp_d = Path(tmp_d_s)
                    lp: Optional[Path] = None
                    try:
                        async with sem:
                            lp = await download_ia_file_async(
                                mid, rf, tmp_d, log_output=False
                            )
                        if not lp:
                            raise Exception(f"DL fail:{mid}/{rf}")
                        ana_data = xtr.extract_structured_data(lp)
                        llm_ok += 1
                        db.conn.execute(
                            "UPDATE job_queue SET analyze_result=?, status='analyzed', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                            [json.dumps(ana_data), jid],
                        )
                        _LOG_.info(f"LLM OK job {jid}.")
                        typer.echo(f"   ✅ LLM OK:{rf}.")
                        _populate_decisoes_from_analysis_result(
                            jid, ana_data, Path(rf).name
                        )
                        dec_stored_count += 1
                    except Exception as e:
                        _LOG_.error(f"LLM fail job {jid}:{e}")
                        nok += 1
                        db.conn.execute(
                            "UPDATE job_queue SET status='failed_analysis', error_message=? WHERE id=?",
                            [f"LLM fail:{e}", jid],
                        )
                        return
                    finally:
                        if lp and lp.exists():
                            try_cleanup(lp.unlink)
        if ana_data:
            _LOG_.debug(f"Meta summary update job {jid}")
            meta_e = {
                "original_url": iurl,
                "publication_date": idt_s,
                "tribunal": tc,
                "original_filename": ofn,
                "analysis_results": ana_data,
            }
            sync_ok = await update_ia_file_level_metadata_summary(mid, rf, meta_e)
            if sync_ok:
                meta_ok += 1
                db.conn.execute(
                    "UPDATE job_queue SET ia_metadata_synced=TRUE, status='ia_metadata_updated', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    [jid],
                )
                _LOG_.info(f"IA meta sync OK job {jid}.")
                typer.echo(f"   ✅ IA meta sync OK:{rf}.")
            else:
                nok += 1
                db.conn.execute(
                    "UPDATE job_queue SET ia_metadata_synced=FALSE, status='failed_metadata_sync', error_message='IA summary fail' WHERE id=?",
                    [jid],
                )
                _LOG_.error(f"IA meta sync FAIL job {jid}.")
                typer.echo(f"   ❌ IA meta sync FAIL:{rf}.", err=True)
        else:
            _LOG_.warning(f"No analysis data job {jid},skip meta sync.")
            nok += 1
            db.conn.execute(
                "UPDATE job_queue SET status='failed_analysis', error_message='No analysis data for sync' WHERE id=?",
                [jid],
            )

    if items:
        tasks = [
            _proc(j, iu, mid, rf, ans, trc, ofn, idts)
            for j, iu, mid, rf, ans, trc, ofn, idts in items
        ]

        async def run_tasks_with_progress():
            await asyncio_tqdm.gather(*tasks, desc="Analyzing items")

        asyncio.run(run_tasks_with_progress())

    typer.echo(
        f"--- Analyze Summary:LLM runs={llm_ok},Meta Updates={meta_ok},Decisions Stored (sets)={dec_stored_count},Failed items={nok} ---"
    )
    _LOG_.info(
        f"Analyze Summary:LLM={llm_ok},MetaUpd={meta_ok},DecStored={dec_stored_count},Fail={nok}"
    )
    return llm_ok, meta_ok, nok, dec_stored_count


@app.command()
def pipeline(
    from_csv: Optional[Path] = typer.Option(None, help="CSV for 'queue' stage."),
    stages: str = typer.Option("archive,analyze,score", help="Pipeline stages."),
    stop_on_error: bool = typer.Option(
        True, "--stop-on-error/--continue-on-error", help="Stop on stage error."
    ),
    limit_archive: Optional[int] = typer.Option(
        None, help="Max items for archive stage."
    ),
    limit_analyze: Optional[int] = typer.Option(
        None, help="Max items for analyze stage."
    ),
    force_analyze: bool = typer.Option(False, help="Force re-analysis."),
    force_score: bool = typer.Option(
        False, help="Force re-calculation of all ratings."
    ),
    archive_concurrency: int = typer.Option(
        config_data.get("internet_archive", {}).get("max_concurrent_uploads", 3),
        help="Archive concurrency.",
    ),
    analyze_concurrency: int = typer.Option(
        config_data.get("analysis", {}).get("max_concurrent_analyses", 2),
        help="Analyze concurrency.",
    ),
):
    """Runs data processing pipeline: queue -> archive -> analyze -> score."""
    sel_stages = [s.strip().lower() for s in stages.split(",")]
    valid_stages = ["queue", "archive", "analyze", "score"]
    for s_name in sel_stages:
        if s_name not in valid_stages:
            typer.echo(f"❌ Invalid stage:'{s_name}'.", err=True)
            _LOG_.error(f"Invalid stage {s_name}")
            raise typer.Exit(1)
        if s_name == "queue" and not from_csv:
            typer.echo("❌ --from-csv for 'queue'.", err=True)
            _LOG_.error("Queue needs CSV")
            raise typer.Exit(1)
    _LOG_.info(f"Pipeline start:{sel_stages}")
    typer.echo(f"🚀 Pipeline:{'→'.join(s.capitalize() for s in sel_stages)}")
    ok_all = True
    for stage in sel_stages:
        typer.echo(f"\n--- Stage:{stage.upper()} ---")
        ok_stage = False
        try:
            if stage == "queue":
                queue(from_csv=from_csv)
                ok_stage = True
            elif stage == "archive":
                _, fails = asyncio.run(
                    archive_stage_logic(
                        limit=limit_archive,
                        max_concurrent_downloads=archive_concurrency,
                    )
                )
                ok_stage = fails == 0
            elif stage == "analyze":
                _, _, fails, _ = asyncio.run(
                    analyze_stage_logic(
                        limit=limit_analyze,
                        force_analysis=force_analyze,
                        max_concurrent_analyses=analyze_concurrency,
                    )
                )
                ok_stage = fails == 0
            elif stage == "score":
                score(force=force_score)
                ok_stage = True
            if ok_stage:
                typer.echo(f"--- Stage {stage.upper()} OK ---")
                _LOG_.info(f"Stage {stage} OK.")
            else:
                typer.echo(f"--- Stage {stage.upper()} Fail/Partial ---")
                _LOG_.warning(f"Stage {stage} Fail/Partial.")
            if not ok_stage:
                ok_all = False
        except typer.Exit:
            ok_all = False
            _LOG_.warning(f"Stage {stage} exited.")
            typer.echo(f"❌ Stage {stage.upper()} exited.", err=True)
            if stop_on_error:
                break
        except Exception as e:
            ok_all = False
            _LOG_.exception(f"Pipeline stage {stage} error:{e}")
            typer.echo(f"❌ Stage {stage.upper()} Error:{e}", err=True)
            if stop_on_error:
                break
    if ok_all:
        typer.echo("\n✅ Pipeline OK!")
    else:
        typer.echo("\n⚠️ Pipeline Errors.")
    typer.echo("\n📊 Final Status:")
    stats()


@app.command()
def score(force: bool = typer.Option(False)):
    _LOG_.info(f"Score(force={force})")
    try:
        from openskill_rating import get_openskill_model, create_rating, rate_teams
    except ImportError:
        _LOG_.error("OpenSkill missing.")
        typer.echo("❌ OpenSkill missing.", err=True)
        return
    if force:
        db.conn.execute("UPDATE decisoes SET processed_for_openskill=FALSE")
        _LOG_.info("Ratings reset.")
        typer.echo("🔄 Ratings reset.")
    decs = db.conn.execute(
        "SELECT id, numero_processo, advogados_polo_ativo, advogados_polo_passivo, resultado FROM decisoes WHERE processed_for_openskill=FALSE AND validation_status='valid' AND resultado IS NOT NULL AND resultado!='' "
    ).fetchall()
    if not decs:
        _LOG_.info("No new decs for score.")
        typer.echo("⭐ No new decs for score.")
        return
    _LOG_.info(f"Scoring {len(decs)} decs.")
    typer.echo(f"⭐ Scoring {len(decs)} decs...")
    osm = get_openskill_model(config_data.get("openskill", {}))
    s, f = 0, 0
    for did, np, aa, ap, r in tqdm(decs, desc="Scoring decisions"):
        if _process_decision_for_rating(osm, did, np, aa, ap, r):
            s += 1
        else:
            f += 1
    db.conn.execute(
        "UPDATE job_queue SET status='scored' WHERE status='ia_metadata_updated'"
    )
    _LOG_.info(f"Score done:{s} ok,{f} nok.")
    typer.echo(f"⭐ Score done:{s} ok,{f} nok.")
    _show_rating_stats()


def _process_decision_for_rating(osm, did, np, aa_json, ap_json, r_str) -> bool:
    try:
        aa = json.loads(aa_json) if aa_json else []
        ap = json.loads(ap_json) if ap_json else []

        def eln(ls):
            return re.sub(r"\\s*\\(OAB[^)]*\\)\\s*", "", ls).strip().upper()

        ta = [n for n in map(eln, aa) if n]
        tp = [n for n in map(eln, ap) if n]
        if not ta and not tp:
            return False
        rl = r_str.lower()
        if rl in ["procedente", "procedente em parte"]:
            mr = "win_a"
        elif rl == "improcedente":
            mr = "win_b"
        elif rl in ["acordo", "homologação de acordo"]:
            mr = "draw"
        else:
            return False
        from openskill_rating import create_rating, rate_teams

        def gocr(n):
            row = db.conn.execute(
                "SELECT mu, sigma FROM ratings WHERE advogado_id=?", [n]
            ).fetchone()
            return (
                create_rating(osm, mu=row[0], sigma=row[1], name=n)
                if row
                else create_rating(osm, name=n)
            )

        tar = [gocr(n) for n in ta] if ta else [create_rating(osm, name="DUMMY_A")]
        tpr = [gocr(n) for n in tp] if tp else [create_rating(osm, name="DUMMY_B")]
        if tar[0].name == "DUMMY_A" and tpr[0].name == "DUMMY_B":
            return False
        n_a, n_b = rate_teams(osm, tar, tpr, mr)
        for rl in [n_a, n_b]:
            for ro in rl:
                if not ro.name.startswith("DUMMY_"):
                    _update_lawyer_rating(ro.name, ro.mu, ro.sigma)
        _store_match_record(did, np, ta, tp, mr)
        db.conn.execute(
            "UPDATE decisoes SET processed_for_openskill=TRUE WHERE id=?", [did]
        )
        return True
    except Exception as e:
        _LOG_.warning(f"Err _process_decision_for_rating for {np}:{e}")
        return False


def _update_lawyer_rating(ln, mu, sigma):
    ex = db.conn.execute(
        "SELECT total_partidas FROM ratings WHERE advogado_id=?", [ln]
    ).fetchone()
    if ex:
        db.conn.execute(
            "UPDATE ratings SET mu=?, sigma=?, total_partidas=?, updated_at=CURRENT_TIMESTAMP WHERE advogado_id=?",
            [mu, sigma, ex[0] + 1, ln],
        )
    else:
        db.conn.execute(
            "INSERT INTO ratings(advogado_id, mu, sigma, total_partidas, created_at, updated_at) VALUES(?,?,?,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
            [ln, mu, sigma],
        )


def _store_match_record(did, np, ta, tp, r):
    try:
        db.conn.execute(
            "INSERT INTO partidas(decisao_id, numero_processo, advogados_polo_ativo, advogados_polo_passivo, resultado_partida, created_at) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
            [did, np, json.dumps(ta), json.dumps(tp), r],
        )
    except Exception as e:
        _LOG_.warning(f"Fail store match {did}:{e}")


def _show_rating_stats():
    try:
        mg = config_data.get("openskill", {}).get("min_games_for_ranking", 3)
        tl = db.conn.execute(
            f"SELECT advogado_id, mu, sigma, total_partidas, mu-3*sigma AS cs FROM ratings WHERE total_partidas>=? ORDER BY cs DESC LIMIT 10",
            [mg],
        ).fetchall()
        if tl:
            typer.echo(f"\n🏆 Top 10 Lawyers(min {mg} games):\n")
            [
                (
                    typer.echo(
                        f"{i:2d}.{n[:30]:<30}|Skill:{cs:6.1f}(μ={mu:5.1f} σ={s:4.1f})|Games:{p:3d}"
                    )
                )
                for i, (n, mu, s, p, cs) in enumerate(tl, 1)
            ]
        tot_l = db.conn.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
        tot_m = db.conn.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]
        typer.echo(f"\n📊 Overall:{tot_l:,} Lawyers,{tot_m:,} Matches")
    except Exception as e:
        _LOG_.warning(f"Stats err:{e}")


@app.command()
def stats():
    try:
        sc = db.conn.execute(
            "SELECT status, COUNT(*) AS count FROM job_queue GROUP BY status ORDER BY status"
        ).fetchall()
        if not sc:
            typer.echo("📊 No jobs in Q.")
            return
        typer.echo("📊 Job Q Status:")
        tj = 0
        for sv, cv in sc:
            ic = {
                "queued": "⏳",
                "archived": "📦",
                "analyzed": "🔍",
                "ia_metadata_updated": "🔄",
                "scored": "⭐",
                "failed": "❌",
                "failed_analysis": "🚫",
                "failed_download": "📥❌",
                "failed_metadata_sync": "📉",
            }.get(sv, "❓")
            typer.echo(f"├── {ic} {sv.replace('_', ' ').title()}:{cv:,} items")
            tj += cv
        typer.echo(f"└── 📈 Total Jobs:{tj:,} items")
        _show_rating_stats()
    except Exception as e:
        if "no such table" in str(e).lower() and "job_queue" in str(e).lower():
            typer.echo("📊 Job Q table missing.")
        else:
            typer.echo(f"❌ Stats Err:{e}", err=True)
            _LOG_.error(f"Stats err:{e}")


@app.command(name="config")
def show_config_command():
    typer.echo(
        f"⚙️ Config:\nDB Path:{config_data['database']['path']}\nIA Master ID:{MASTER_IA_ITEM_ID}\nOpenSkill μ:{config_data.get('openskill', {}).get('mu')}"
    )


@app.command("diario")
def diario_cmd(
    action: str = typer.Argument(..., help="list,stats"),
    tribunal: Optional[str] = typer.Option(None),
    status: Optional[str] = typer.Option(None),
    limit: int = typer.Option(20),
):
    if action == "stats":
        stats()
    elif action == "list":
        q = "SELECT id, url, date, tribunal, status, ia_identifier, ia_remote_filename FROM job_queue"
        cd, pr = [], []
        if tribunal:
            cd.append("tribunal=?")
            pr.append(tribunal.lower())
        if status:
            cd.append("status=?")
            pr.append(status.lower())
        if cd:
            q += " WHERE " + " AND ".join(cd)
        q += " ORDER BY created_at DESC LIMIT ?"
        pr.append(limit)
        rs = db.conn.execute(q, pr).fetchall()
        if not rs:
            typer.echo("No diarios.")
            return
        typer.echo(f"📋 Found {len(rs)} diarios:")
        for r in rs:
            typer.echo(
                f" ID:{r[0]} Date:{r[2]} Trib:{r[3].upper()} Status:{r[4]} IA:{r[5]}/{r[6]} URL:{r[1]}"
            )
    else:
        typer.echo(f"❌ Unknown diario action:{action}", err=True)
        raise typer.Exit(1)


@app.command("db")
def database_cmd(
    action: str = typer.Argument(..., help="migrate,status,backup,reset,sync"),
    force: bool = typer.Option(False),
):
    if action == "migrate":
        _db_migrate()
    elif action == "status":
        _db_status()
    elif action == "backup":
        _db_backup()
    elif action == "reset":
        _db_reset(force)
    elif action == "sync":
        _db_sync(force)
    else:
        typer.echo(f"❌ Unknown DB action:{action}", err=True)
        raise typer.Exit(1)


def _db_sync(force: bool):
    """Sync database with Internet Archive."""
    try:
        from ia_database_sync import main as sync_main
        import sys

        typer.echo("🔄 Syncing database with Internet Archive...")

        old_argv = sys.argv
        new_argv = ["ia_database_sync.py", "sync"]
        if force:
            new_argv.append("--force")

        sys.argv = new_argv

        try:
            sync_main()
            typer.echo("✅ Database sync completed")
        except SystemExit as e:
            if e.code != 0:
                typer.echo(
                    f"❌ Database sync script exited with code {e.code}", err=True
                )
            else:
                typer.echo("✅ Database sync completed")
        finally:
            sys.argv = old_argv

    except ImportError:
        _LOG_.error("ia_database_sync.py not found.")
        typer.echo("❌ ia_database_sync.py not found.", err=True)
    except Exception as e:
        _LOG_.error(f"Database sync failed: {e}")
        typer.echo(f"❌ Database sync failed: {e}", err=True)


def _db_migrate():
    try:
        from migration_runner import run_migrations

        typer.echo("🔄 Migrating...")
        run_migrations()
        typer.echo("✅ Migrations done.")
    except ImportError:
        _LOG_.error("migration_runner.py not found.")
        typer.echo("❌ migration_runner.py not found.", err=True)
    except Exception as e:
        _LOG_.error(f"Migration failed:{e}")
        typer.echo(f"❌ Migration fail:{e}", err=True)


def _db_status():
    typer.echo(f"ℹ️ DB Path:{config_data['database']['path']}")
    stats()


def _db_backup():
    dbf = Path(config_data["database"]["path"])
    if not dbf.exists():
        _LOG_.error(f"DB not found for backup:{dbf}")
        typer.echo(f"❌ DB not found:{dbf}", err=True)
        return
    bkd = dbf.parent / "backups"
    bkd.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkf = bkd / f"{dbf.stem}_backup_{ts}{dbf.suffix}"
    try:
        import shutil

        shutil.copy2(dbf, bkf)
        _LOG_.info(f"DB backup created:{bkf}")
        typer.echo(f"✅ DB backup:{bkf} ({bkf.stat().st_size / 1e6:.2f}MB)")
    except Exception as e:
        _LOG_.error(f"DB Backup failed:{e}")
        typer.echo(f"❌ Backup fail:{e}", err=True)


def _db_reset(force: bool):
    dbf = Path(config_data["database"]["path"])
    if not dbf.exists():
        _LOG_.info(f"DB {dbf} not found, migrating.")
        typer.echo(f"ℹ️ DB {dbf} not found. Migrating.")
        _db_migrate()
        return
    if not force and not typer.confirm(
        f"⚠️ DELETE {dbf}? IRREVERSIBLE. Confirm?", abort=False
    ):
        _LOG_.info("DB reset cancelled.")
        typer.echo("❌ Reset cancelled.")
        return
    try:
        db.close()
        dbf.unlink()
        _LOG_.info(f"DB {dbf} deleted.")
        typer.echo(f"🗑️ Deleted {dbf}.")
        db.connect()
        _LOG_.info("DB reset&reinit.")
        typer.echo("✅ DB reset & reinit.")
    except Exception as e:
        _LOG_.error(f"DB reset fail:{e}")
        typer.echo(f"❌ DB reset fail:{e}", err=True)
        try_cleanup(db.connect)


def try_cleanup(func, *args, **kwargs):
    """Attempts to execute a function, logs any exception at debug level. Useful for cleanup operations."""
    try:
        func(*args, **kwargs)
    except Exception as e:
        _LOG_.debug(f"try_cleanup caught exception during {func.__name__}: {e}")


if __name__ == "__main__":
    app()
