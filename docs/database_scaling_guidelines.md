# Database Scaling Guidelines

As the volume of processed diarios grows, the DuckDB file will increase in size. To keep the system performant:

- **Archive old snapshots** to the Internet Archive regularly using `ia_database_sync.py upload`.
- **Vacuum** tables periodically to reclaim space: `duckdb -c "VACUUM" data/causaganha.duckdb`.
- **Split workloads** by year if the file exceeds several gigabytes; use multiple DuckDB files and merge results when reporting.
- **Consider MotherDuck or Postgres** if concurrent writers become common.

These steps help avoid runaway file growth and keep queries fast on commodity hardware.
