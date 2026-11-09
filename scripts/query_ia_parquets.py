#!/usr/bin/env python3
"""Busca parquets de outros tribunais no Internet Archive."""

import duckdb


def main():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    manifest_url = "https://archive.org/download/causaganha-catalog/manifest.parquet"
    print("Consultando manifest do IA...")
    df = con.execute(f"""
        SELECT tribunal, table_name, file_name, ia_item, ia_url
        FROM read_parquet('{manifest_url}')
        WHERE table_name IN ('comunicacoes', 'textos')
          AND tribunal IN ('TJSP', 'TJRJ', 'TJMG', 'TJBA', 'TJDFT', 'STJ', 'TRF1')
        ORDER BY tribunal, ia_item DESC
        LIMIT 40
    """).df()
    print(df.to_string())


if __name__ == "__main__":
    main()
