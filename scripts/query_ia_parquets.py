#!/usr/bin/env python3
"""Busca parquets de comunicacoes para amostra no IA."""

import duckdb

def main():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    manifest_url = "https://archive.org/download/causaganha-catalog/manifest.parquet"
    print("Consultando manifest...")
    df = con.execute(f"""
        SELECT tribunal, table_name, file_name, ia_item, ia_url
        FROM read_parquet('{manifest_url}')
        WHERE table_name = 'comunicacoes'
          AND tribunal IN ('TJRO', 'TJAC', 'TJRR', 'TJAP', 'TSTO', 'TRF1')
        ORDER BY tribunal, ia_item DESC
        LIMIT 20
    """).df()
    print(df.to_string())

if __name__ == "__main__":
    main()
