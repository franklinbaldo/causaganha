# causaganha/core/r2_queries.py
"""
Direct DuckDB queries against Cloudflare R2 stored snapshots.

Enables remote database analysis without local downloads using DuckDB's
native S3-compatible storage integration.
"""

import duckdb
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from dataclasses import dataclass

from .r2_storage import CloudflareR2Storage, R2Config

logger = logging.getLogger(__name__)


@dataclass
class R2QueryConfig:
    """Configuration for R2 remote queries."""
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str = "causa-ganha"
    
    @property
    def s3_endpoint(self) -> str:
        """S3-compatible endpoint for DuckDB."""
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


class R2DuckDBClient:
    """
    Client for executing DuckDB queries directly against R2-stored snapshots.
    
    Features:
    - Remote snapshot queries without download
    - Multi-snapshot temporal analysis
    - Cost-efficient read-only operations
    - Automatic S3 configuration for DuckDB
    """
    
    def __init__(self, config: R2QueryConfig):
        self.config = config
        self.conn = None
        self.r2_storage = None
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup DuckDB connection with S3/R2 configuration."""
        self.conn = duckdb.connect(':memory:')
        
        # Configure S3 settings for R2
        self.conn.execute(f"""
            SET s3_region = 'auto';
            SET s3_endpoint = '{self.config.s3_endpoint}';
            SET s3_access_key_id = '{self.config.access_key_id}';
            SET s3_secret_access_key = '{self.config.secret_access_key}';
            SET s3_use_ssl = true;
        """)
        
        # Initialize R2 storage client for metadata operations
        r2_config = R2Config(
            account_id=self.config.account_id,
            access_key_id=self.config.access_key_id,
            secret_access_key=self.config.secret_access_key,
            bucket_name=self.config.bucket_name
        )
        self.r2_storage = CloudflareR2Storage(r2_config)
        
        logger.info("DuckDB configured for R2 remote queries")
    
    @classmethod
    def from_env(cls) -> 'R2DuckDBClient':
        """Create client from environment variables."""
        import os
        
        config = R2QueryConfig(
            account_id=os.getenv('CLOUDFLARE_ACCOUNT_ID'),
            access_key_id=os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID'),
            secret_access_key=os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY'),
            bucket_name=os.getenv('CLOUDFLARE_R2_BUCKET', 'causa-ganha')
        )
        
        if not all([config.account_id, config.access_key_id, config.secret_access_key]):
            raise ValueError("Missing required R2 environment variables")
            
        return cls(config)
    
    def get_snapshot_s3_url(self, snapshot_key: str) -> str:
        """Generate S3 URL for snapshot."""
        return f"s3://{self.config.bucket_name}/{snapshot_key}"
    
    def list_available_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots with metadata."""
        return self.r2_storage.list_snapshots()
    
    def query_latest_snapshot(self, query: str) -> pd.DataFrame:
        """Execute query against the latest snapshot."""
        latest_key = self.r2_storage.get_latest_snapshot_key()
        if not latest_key:
            raise ValueError("No snapshots found in R2")
        
        return self.query_snapshot(latest_key, query)
    
    def query_snapshot(self, snapshot_key: str, query: str) -> pd.DataFrame:
        """
        Execute query against specific snapshot.
        
        Args:
            snapshot_key: S3 key of snapshot
            query: SQL query to execute
            
        Returns:
            Query results as DataFrame
        """
        # Note: For compressed snapshots, we need to download and decompress first
        # DuckDB doesn't natively support compressed S3 objects
        if snapshot_key.endswith('.zst'):
            logger.warning("Compressed snapshots require local decompression for queries")
            
            # Download and decompress temporarily
            temp_path = Path("temp_query_snapshot.duckdb")
            try:
                decompressed_path = self.r2_storage.download_snapshot(snapshot_key, temp_path)
                
                # Query local file
                result = self.conn.execute(f"""
                    SELECT * FROM read_csv_auto('{decompressed_path}') 
                    LIMIT 0
                """).df()
                
                # Actually execute the user's query
                self.conn.execute(f"ATTACH '{decompressed_path}' AS snapshot")
                result = self.conn.execute(query).df()
                self.conn.execute("DETACH snapshot")
                
                return result
                
            finally:
                # Cleanup
                if temp_path.exists():
                    temp_path.unlink()
        
        else:
            # Direct S3 query (for uncompressed snapshots)
            s3_url = self.get_snapshot_s3_url(snapshot_key)
            
            # Attach remote database
            self.conn.execute(f"ATTACH '{s3_url}' AS snapshot (READ_ONLY)")
            
            try:
                result = self.conn.execute(query).df()
                return result
            finally:
                self.conn.execute("DETACH snapshot")
    
    def get_latest_rankings(self, limit: int = 20) -> pd.DataFrame:
        """Get current TrueSkill rankings from latest snapshot."""
        query = f"""
        SELECT 
            advogado_id,
            mu,
            sigma,
            mu - 3 * sigma as conservative_skill,
            total_partidas,
            ROW_NUMBER() OVER (ORDER BY mu DESC) as ranking_position
        FROM snapshot.ratings 
        WHERE total_partidas > 0
        ORDER BY mu DESC 
        LIMIT {limit}
        """
        
        return self.query_latest_snapshot(query)
    
    def compare_snapshots(self, 
                         snapshot1_key: str, 
                         snapshot2_key: str,
                         metric: str = "mu") -> pd.DataFrame:
        """
        Compare metrics between two snapshots.
        
        Args:
            snapshot1_key: First snapshot (typically older)
            snapshot2_key: Second snapshot (typically newer) 
            metric: Column to compare (mu, sigma, total_partidas)
            
        Returns:
            DataFrame with comparison results
        """
        # This requires downloading both snapshots for join operation
        logger.info("Comparing %s between snapshots", metric)
        
        # Download both snapshots
        temp_path1 = Path("temp_snapshot1.duckdb")
        temp_path2 = Path("temp_snapshot2.duckdb")
        
        try:
            path1 = self.r2_storage.download_snapshot(snapshot1_key, temp_path1)
            path2 = self.r2_storage.download_snapshot(snapshot2_key, temp_path2)
            
            # Attach both databases
            self.conn.execute(f"ATTACH '{path1}' AS snap1")
            self.conn.execute(f"ATTACH '{path2}' AS snap2")
            
            # Execute comparison query
            query = f"""
            SELECT 
                s2.advogado_id,
                s1.{metric} as {metric}_before,
                s2.{metric} as {metric}_after,
                s2.{metric} - s1.{metric} as {metric}_delta,
                s2.total_partidas - s1.total_partidas as new_matches
            FROM snap2.ratings s2
            JOIN snap1.ratings s1 ON s2.advogado_id = s1.advogado_id
            WHERE s2.{metric} != s1.{metric}
            ORDER BY {metric}_delta DESC
            """
            
            result = self.conn.execute(query).df()
            
            return result
            
        finally:
            # Cleanup
            self.conn.execute("DETACH snap1") if 'snap1' in str(self.conn.execute("SHOW DATABASES").df()) else None
            self.conn.execute("DETACH snap2") if 'snap2' in str(self.conn.execute("SHOW DATABASES").df()) else None
            
            for temp_path in [temp_path1, temp_path2]:
                if temp_path.exists():
                    temp_path.unlink()
    
    def get_temporal_analysis(self, 
                             days_back: int = 30,
                             advogado_id: Optional[str] = None) -> pd.DataFrame:
        """
        Analyze trends over multiple snapshots.
        
        Args:
            days_back: Number of days to look back
            advogado_id: Specific lawyer to analyze (optional)
            
        Returns:
            DataFrame with temporal trends
        """
        # Get snapshots from the specified period
        snapshots = self.list_available_snapshots()
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        relevant_snapshots = [
            s for s in snapshots 
            if datetime.fromisoformat(s['last_modified'].replace('Z', '+00:00')) >= cutoff_date
        ]
        
        if len(relevant_snapshots) < 2:
            logger.warning("Only %d snapshots found in last %d days", len(relevant_snapshots), days_back)
            return pd.DataFrame()
        
        logger.info("Analyzing %d snapshots over %d days", len(relevant_snapshots), days_back)
        
        # For now, compare oldest vs newest in the period
        oldest_snapshot = relevant_snapshots[-1]  # List is sorted newest first
        newest_snapshot = relevant_snapshots[0]
        
        comparison = self.compare_snapshots(
            oldest_snapshot['key'], 
            newest_snapshot['key']
        )
        
        # Add metadata
        comparison['analysis_period_days'] = days_back
        comparison['snapshots_analyzed'] = len(relevant_snapshots)
        comparison['oldest_snapshot'] = oldest_snapshot['last_modified']
        comparison['newest_snapshot'] = newest_snapshot['last_modified']
        
        # Filter by specific lawyer if requested
        if advogado_id:
            comparison = comparison[comparison['advogado_id'] == advogado_id]
        
        return comparison
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics from latest snapshot."""
        query = """
        SELECT 
            COUNT(*) as total_lawyers,
            COUNT(CASE WHEN total_partidas > 0 THEN 1 END) as active_lawyers,
            AVG(CASE WHEN total_partidas > 0 THEN mu END) as avg_rating,
            MAX(total_partidas) as max_matches,
            SUM(total_partidas) as total_matches_played
        FROM snapshot.ratings
        """
        
        result = self.query_latest_snapshot(query)
        return result.iloc[0].to_dict()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def main():
    """CLI interface for R2 queries."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query Cloudflare R2 snapshots')
    parser.add_argument('action', choices=['rankings', 'stats', 'compare', 'trends'],
                       help='Query type to execute')
    parser.add_argument('--limit', type=int, default=20, help='Limit for rankings')
    parser.add_argument('--snapshot1', help='First snapshot key for comparison')
    parser.add_argument('--snapshot2', help='Second snapshot key for comparison')
    parser.add_argument('--days', type=int, default=30, help='Days back for trends')
    parser.add_argument('--lawyer', help='Specific lawyer ID for analysis')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize R2 client
        client = R2DuckDBClient.from_env()
        
        if args.action == 'rankings':
            rankings = client.get_latest_rankings(args.limit)
            print(f"🏆 Top {args.limit} TrueSkill Rankings:")
            print(rankings.to_string(index=False))
            
        elif args.action == 'stats':
            stats = client.get_system_statistics()
            print("📊 System Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
                
        elif args.action == 'compare':
            if not args.snapshot1 or not args.snapshot2:
                print("Error: --snapshot1 and --snapshot2 required for comparison")
                exit(1)
                
            comparison = client.compare_snapshots(args.snapshot1, args.snapshot2)
            print(f"📈 Snapshot Comparison:")
            print(comparison.to_string(index=False))
            
        elif args.action == 'trends':
            trends = client.get_temporal_analysis(args.days, args.lawyer)
            print(f"📅 Temporal Analysis ({args.days} days):")
            print(trends.to_string(index=False))
            
    except (OSError, RuntimeError, ValueError, ConnectionError) as e:
        logger.error("Query failed: %s", e)
        exit(1)
        
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    main()