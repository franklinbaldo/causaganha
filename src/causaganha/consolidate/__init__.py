"""Consolidation pipeline: DJEN ZIPs → 10 normalized Parquet tables → IA upload.

BDD-driven rewrite of scripts/pipeline/consolidate.py focused on bounded
memory usage and clear behavioral contracts.
"""
