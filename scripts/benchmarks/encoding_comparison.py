r"""A0e — encoding comparison benchmark (gate for A2/A3).

Compares compressed bytes for the current schema vs the A2/A3 candidate
encodings on synthetic data that matches production cardinality patterns:
  - UUID columns: 36-char string  vs  16-byte BLOB
  - CNJ column  : 20-char string  vs  DECIMAL(20,0)
  - hash column : 64-char string  vs  32-byte BLOB (SHA-256 hex)

Only proceeds to A2/A3 migration if the measured savings justify the cost of
a major schema bump + re-upload of all IA items.  Running this on a real
production Parquet (--real-file) is more reliable than the synthetic version.

Usage:
    # Synthetic (no IA access needed)
    uv run python scripts/benchmarks/encoding_comparison.py

    # Against a real file (recommended before deciding on A2/A3)
    uv run python scripts/benchmarks/encoding_comparison.py \\
        --real-file /path/to/comunicacoes.parquet
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import duckdb


N_ROWS = 200_000


def _compressed_size(con: duckdb.DuckDBPyConnection, path: Path, col: str) -> int:
    rows = con.execute(
        f"""
        SELECT SUM(total_compressed_size)
        FROM parquet_metadata('{path}')
        WHERE path_in_schema = '{col}'
        """
    ).fetchone()
    return int(rows[0] or 0)


def run_synthetic() -> None:
    print(f"Synthetic benchmark — {N_ROWS:,} rows, duckdb {duckdb.__version__}")
    print()

    con = duckdb.connect()

    with tempfile.TemporaryDirectory() as tmpdir:
        # ── v3 baseline ────────────────────────────────────────────────
        con.execute(
            f"""
            CREATE OR REPLACE TABLE v3 AS
            SELECT
                gen_random_uuid()::VARCHAR                  AS id,
                gen_random_uuid()::VARCHAR                  AS original_id,
                gen_random_uuid()::VARCHAR                  AS texto_id,
                printf('%020d', range % 5000000)            AS numero_processo,
                sha256(range::VARCHAR)::VARCHAR             AS hash
            FROM range({N_ROWS})
            """
        )
        p3 = Path(tmpdir) / "v3.parquet"
        con.execute(f"COPY v3 TO '{p3}' (FORMAT PARQUET, COMPRESSION ZSTD)")

        v3_id = _compressed_size(con, p3, "id")
        v3_orig = _compressed_size(con, p3, "original_id")
        v3_txt = _compressed_size(con, p3, "texto_id")
        v3_cnj = _compressed_size(con, p3, "numero_processo")
        v3_hash = _compressed_size(con, p3, "hash")
        v3_total = v3_id + v3_orig + v3_txt + v3_cnj + v3_hash

        # ── v4 candidate ───────────────────────────────────────────────
        # id/texto_id → BLOB (16 bytes raw UUID)
        # original_id stays VARCHAR — external DJEN source, not guaranteed UUID
        # CNJ  → DECIMAL(20,0) — stores as FIXED_LEN_BYTE_ARRAY, ~16 bytes
        # hash → BLOB (32 bytes raw SHA-256)
        con.execute(
            f"""
            CREATE OR REPLACE TABLE v4 AS
            SELECT
                gen_random_uuid()                           AS id,
                gen_random_uuid()::VARCHAR                  AS original_id,
                gen_random_uuid()                           AS texto_id,
                CAST(printf('%020d', range % 5000000) AS DECIMAL(20, 0))
                                                            AS numero_processo,
                unhex(sha256(range::VARCHAR)::VARCHAR)      AS hash
            FROM range({N_ROWS})
            """
        )
        p4 = Path(tmpdir) / "v4.parquet"
        con.execute(f"COPY v4 TO '{p4}' (FORMAT PARQUET, COMPRESSION ZSTD)")

        v4_id = _compressed_size(con, p4, "id")
        v4_orig = _compressed_size(con, p4, "original_id")
        v4_txt = _compressed_size(con, p4, "texto_id")
        v4_cnj = _compressed_size(con, p4, "numero_processo")
        v4_hash = _compressed_size(con, p4, "hash")
        v4_total = v4_id + v4_orig + v4_txt + v4_cnj + v4_hash

    def _pct(a: int, b: int) -> str:
        if b == 0:
            return "N/A"
        return f"{100 * (a - b) / b:+.1f}%"

    def _kb(n: int) -> str:
        return f"{n / 1024:.1f} KiB"

    print(f"{'Column':<22} {'v3 (current)':>14} {'v4 (candidate)':>14} {'Delta':>9}  Notes")
    print("-" * 75)
    rows = [
        ("id (UUID)", v3_id, v4_id, "string→uuid blob"),
        ("original_id", v3_orig, v4_orig, "string (unchanged — external source)"),
        ("texto_id", v3_txt, v4_txt, "string→uuid blob"),
        ("numero_processo", v3_cnj, v4_cnj, "string→decimal(20,0)"),
        ("hash", v3_hash, v4_hash, "hex string→bytes"),
    ]
    for name, v3, v4, notes in rows:
        print(f"{name:<22} {_kb(v3):>14} {_kb(v4):>14} {_pct(v4, v3):>9}  {notes}")
    print("-" * 75)
    print(
        f"{'TOTAL (5 cols)':<22} {_kb(v3_total):>14} {_kb(v4_total):>14} "
        f"{_pct(v4_total, v3_total):>9}"
    )
    print()
    print("⚠  This is SYNTHETIC data.  Run with --real-file against a production")
    print("   Parquet before deciding on A2/A3 migration.  ZSTD+dictionary on the")
    print("   real repetition pattern may compress the string columns differently.")
    con.close()


def run_real_file(path: str) -> None:
    """Compare actual column sizes in a production file vs estimated v4 savings."""
    con = duckdb.connect()

    print(f"\nReal-file analysis: {path}")
    print("(v4 candidate sizes are extrapolated, not actual — run synthetic for exact delta)")
    print()

    cols = con.execute(
        f"""
        SELECT path_in_schema, SUM(total_compressed_size) AS bytes
        FROM parquet_metadata('{path}')
        GROUP BY path_in_schema
        ORDER BY bytes DESC
        """
    ).fetchall()

    total = sum(r[1] for r in cols)
    print(f"{'Column':<35} {'Compressed':>14} {'% total':>8}")
    print("-" * 62)
    for col, sz in cols:
        pct = 100 * sz / total if total else 0
        note = ""
        if col in ("id", "original_id", "texto_id", "comunicacao_id", "advogado_id", "parte_id"):
            note = "  ← UUID candidate (A2)"
        elif col == "numero_processo":
            note = "  ← CNJ candidate (A3)"
        elif col == "hash":
            note = "  ← hash candidate (A5)"
        print(f"{col:<35} {sz / 1024:>13.1f} KiB {pct:>7.1f}%{note}")
    print("-" * 62)
    print(f"{'TOTAL':<35} {total / 1024:>13.1f} KiB")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="A0e: encoding comparison for A2/A3 gate")
    ap.add_argument("--real-file", help="Path to a real production Parquet for analysis")
    args = ap.parse_args()

    if args.real_file:
        run_real_file(args.real_file)
    else:
        run_synthetic()


if __name__ == "__main__":
    main()
