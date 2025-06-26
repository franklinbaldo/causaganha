#!/usr/bin/env python3
"""
Playwright-based PDF Discovery - Navigate TJRO website like a real browser

This script uses Playwright to discover PDFs from the TJRO website by navigating
the site like a real user, bypassing bot detection systems.

Installation:
    uv add playwright
    uv run playwright install

Usage:
    python scripts/playwright_discovery.py --start-year 2020 --end-year 2025
    python scripts/playwright_discovery.py --year 2024
    python scripts/playwright_discovery.py --latest
"""

import sys
import argparse
import json
import csv
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import CausaGanhaDB

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Page, Browser
except ImportError:
    logger.error("Playwright not installed. Run: uv add playwright && uv run playwright install")
    sys.exit(1)


class TJROPlaywrightDiscovery:
    """Discover PDFs using Playwright browser automation."""
    
    def __init__(self, db: CausaGanhaDB, headless: bool = True):
        self.db = db
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.discovered_count = 0
        self.error_count = 0
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        
        # Launch browser with realistic settings
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-dev-shm-usage'
            ]
        )
        
        # Create context with realistic user agent and viewport
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='pt-BR'
        )
        
        # Create page
        self.page = await self.context.new_page()
        
        # Add stealth measures
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def discover_year(self, year: int) -> Dict[str, int]:
        """Discover all PDFs for a specific year."""
        logger.info(f"🔍 Discovering PDFs for year {year}")
        
        try:
            # Navigate to the year list API endpoint
            url = f"https://www.tjro.jus.br/diario_oficial/list.php?ano={year}"
            logger.debug(f"Navigating to: {url}")
            
            # Navigate with retry logic
            response = await self._navigate_with_retry(url)
            if not response:
                return {"total": 0, "new": 0, "existing": 0, "errors": 1}
            
            # Wait for content to load
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Get page content
            content = await self.page.content()
            
            # Check if we got blocked
            if 'Página Bloqueada' in content or 'support ID' in content:
                logger.warning(f"⚠️ Access blocked for year {year}")
                # Wait longer and try again
                await asyncio.sleep(5)
                return {"total": 0, "new": 0, "existing": 0, "errors": 1}
            
            # Try to get JSON data from page
            try:
                # Look for JSON in page source or extract from API response
                json_data = await self.page.evaluate("""
                    () => {
                        // Try to find JSON data in various ways
                        const bodyText = document.body.innerText;
                        
                        // Check if it's direct JSON
                        try {
                            return JSON.parse(bodyText);
                        } catch (e) {
                            // Check for JSON in script tags
                            const scripts = document.querySelectorAll('script');
                            for (let script of scripts) {
                                const text = script.innerText;
                                if (text.includes('[') && text.includes('{')) {
                                    try {
                                        const match = text.match(/\\[.*\\]/s);
                                        if (match) {
                                            return JSON.parse(match[0]);
                                        }
                                    } catch (e2) {
                                        continue;
                                    }
                                }
                            }
                            return null;
                        }
                    }
                """)
                
                if json_data and isinstance(json_data, list):
                    return await self._process_pdf_list(json_data, year)
                else:
                    # Try alternative: look for PDF links in HTML
                    pdf_links = await self.page.evaluate("""
                        () => {
                            const links = [];
                            const anchors = document.querySelectorAll('a[href*=".pdf"], a[href*="recupera.php"]');
                            anchors.forEach(a => {
                                links.push({
                                    url: a.href,
                                    text: a.innerText || a.textContent
                                });
                            });
                            return links;
                        }
                    """)
                    
                    if pdf_links:
                        logger.info(f"Found {len(pdf_links)} PDF links for year {year}")
                        return await self._process_pdf_links(pdf_links, year)
                    else:
                        logger.warning(f"No JSON data or PDF links found for year {year}")
                        return {"total": 0, "new": 0, "existing": 0, "errors": 1}
                        
            except Exception as e:
                logger.error(f"Error processing page content for year {year}: {e}")
                return {"total": 0, "new": 0, "existing": 0, "errors": 1}
                
        except Exception as e:
            logger.error(f"Failed to discover PDFs for year {year}: {e}")
            self.error_count += 1
            return {"total": 0, "new": 0, "existing": 0, "errors": 1}
    
    async def discover_latest(self) -> Dict[str, int]:
        """Discover latest PDFs."""
        logger.info("🔍 Discovering latest PDFs")
        
        try:
            url = "https://www.tjro.jus.br/diario_oficial/data-ultimo-diario.php"
            
            response = await self._navigate_with_retry(url)
            if not response:
                return {"total": 0, "new": 0, "existing": 0, "errors": 1}
            
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Get JSON data
            json_data = await self.page.evaluate("""
                () => {
                    try {
                        return JSON.parse(document.body.innerText);
                    } catch (e) {
                        return null;
                    }
                }
            """)
            
            if json_data and isinstance(json_data, list):
                return await self._process_pdf_list(json_data, priority=10)
            else:
                logger.warning("No JSON data found for latest PDFs")
                return {"total": 0, "new": 0, "existing": 0, "errors": 1}
                
        except Exception as e:
            logger.error(f"Failed to discover latest PDFs: {e}")
            return {"total": 0, "new": 0, "existing": 0, "errors": 1}
    
    async def discover_range(self, start_year: int, end_year: int) -> Dict[str, Dict]:
        """Discover PDFs for a range of years."""
        logger.info(f"🎯 Starting Playwright discovery: {start_year} to {end_year}")
        
        results = {}
        total_stats = {"total": 0, "new": 0, "existing": 0, "errors": 0}
        
        for year in range(start_year, end_year + 1):
            try:
                year_stats = await self.discover_year(year)
                results[str(year)] = year_stats
                
                # Update totals
                for key in total_stats:
                    total_stats[key] += year_stats.get(key, 0)
                
                logger.info(f"✅ Year {year}: {year_stats}")
                
                # Rate limiting - be respectful
                if year < end_year:
                    wait_time = 3 + (self.error_count * 2)  # Increase wait time if errors
                    logger.info(f"⏳ Waiting {wait_time} seconds before next year...")
                    await asyncio.sleep(wait_time)
                    
            except KeyboardInterrupt:
                logger.info(f"🛑 Discovery interrupted at year {year}")
                break
            except Exception as e:
                logger.error(f"Failed to process year {year}: {e}")
                self.error_count += 1
                continue
        
        results["_totals"] = total_stats
        logger.info(f"🎉 Playwright discovery complete: {total_stats}")
        
        return results
    
    async def _navigate_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """Navigate to URL with retry logic."""
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1} to navigate to: {url}")
                
                response = await self.page.goto(
                    url, 
                    wait_until='domcontentloaded',
                    timeout=30000
                )
                
                if response and response.status == 200:
                    return True
                else:
                    logger.warning(f"HTTP {response.status if response else 'No response'} for {url}")
                    
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.debug(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        return False
    
    async def _process_pdf_list(self, pdf_data: List[Dict], year: int = None, priority: int = 0) -> Dict[str, int]:
        """Process list of PDF data from API."""
        total_count = len(pdf_data)
        new_count = 0
        existing_count = 0
        
        logger.info(f"📄 Processing {total_count} PDFs")
        
        for pdf_info in pdf_data:
            try:
                if await self._add_to_discovery_queue(pdf_info, year, priority):
                    new_count += 1
                    self.discovered_count += 1
                else:
                    existing_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process PDF info: {pdf_info}, error: {e}")
                continue
        
        return {"total": total_count, "new": new_count, "existing": existing_count, "errors": 0}
    
    async def _process_pdf_links(self, pdf_links: List[Dict], year: int) -> Dict[str, int]:
        """Process PDF links found in HTML."""
        total_count = len(pdf_links)
        new_count = 0
        existing_count = 0
        
        for link_info in pdf_links:
            try:
                # Extract date and number from URL or text
                url = link_info['url']
                text = link_info.get('text', '')
                
                # Try to parse date from URL
                pdf_data = self._parse_pdf_info_from_url(url, text, year)
                if pdf_data and await self._add_to_discovery_queue(pdf_data, year):
                    new_count += 1
                    self.discovered_count += 1
                else:
                    existing_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process PDF link: {link_info}, error: {e}")
                continue
        
        return {"total": total_count, "new": new_count, "existing": existing_count, "errors": 0}
    
    def _parse_pdf_info_from_url(self, url: str, text: str, year: int) -> Optional[Dict]:
        """Parse PDF info from URL and text."""
        import re
        
        # Try to extract number and date from URL
        # Example: recupera.php?numero=249&ano=2024
        number_match = re.search(r'numero=([^&]+)', url)
        year_match = re.search(r'ano=(\d{4})', url)
        
        if number_match:
            number = number_match.group(1)
            url_year = int(year_match.group(1)) if year_match else year
            
            # For now, use a default date (this could be improved)
            # In a real implementation, you'd extract this from the page context
            date_str = f"{url_year}-12-01"  # Default date
            
            return {
                "year": str(url_year),
                "month": "12",
                "day": "01",
                "number": number,
                "url": url
            }
        
        return None
    
    async def _add_to_discovery_queue(self, pdf_info: Dict, year: int = None, priority: int = 0) -> bool:
        """Add PDF info to discovery queue."""
        try:
            # Extract and validate required fields
            pdf_url = pdf_info.get('url', '').strip()
            if not pdf_url:
                logger.warning(f"PDF info missing URL: {pdf_info}")
                return False
            
            # Parse date
            year_val = year or int(pdf_info.get('year', 0))
            month_val = int(pdf_info.get('month', 0))
            day_val = int(pdf_info.get('day', 0))
            
            if not all([year_val, month_val, day_val]):
                logger.warning(f"Invalid date components in PDF info: {pdf_info}")
                return False
            
            date_str = f"{year_val}-{month_val:02d}-{day_val:02d}"
            number_str = pdf_info.get('number', '').strip()
            
            # Check if already in database
            existing = self.db.execute("""
                SELECT id FROM pdf_discovery_queue 
                WHERE url = ? OR (date = ? AND number = ?)
            """, (pdf_url, date_str, number_str)).fetchone()
            
            if existing:
                return False
            
            # Add to queue
            self.db.execute("""
                INSERT INTO pdf_discovery_queue 
                (url, date, number, year, priority, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                pdf_url,
                date_str,
                number_str,
                year_val,
                priority,
                json.dumps(pdf_info)
            ))
            
            logger.debug(f"➕ Added to queue: {date_str} - {number_str}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add PDF to queue: {pdf_info}, error: {e}")
            return False


async def export_to_csv(db: CausaGanhaDB, output_file: Path):
    """Export discovery queue to CSV."""
    logger.info(f"📊 Exporting discovery queue to {output_file}")
    
    # Get all items from discovery queue
    items = db.execute("""
        SELECT 
            id, url, date, number, year, status, priority, 
            attempts, last_attempt, error_message, metadata, 
            created_at, updated_at
        FROM pdf_discovery_queue
        ORDER BY year DESC, date DESC, number
    """).fetchall()
    
    if not items:
        logger.warning("No items found in discovery queue")
        return
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow([
            'id', 'url', 'date', 'number', 'year', 'status', 'priority',
            'attempts', 'last_attempt', 'error_message', 'metadata',
            'created_at', 'updated_at'
        ])
        
        # Data rows
        for item in items:
            writer.writerow(item)
    
    logger.info(f"✅ Exported {len(items)} items to {output_file}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Discover PDFs from TJRO using Playwright browser automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/playwright_discovery.py --start-year 2020 --end-year 2025
  python scripts/playwright_discovery.py --year 2024
  python scripts/playwright_discovery.py --latest
  python scripts/playwright_discovery.py --export-only
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--start-year', type=int, help='Start year for range discovery')
    group.add_argument('--year', type=int, help='Single year to discover')
    group.add_argument('--latest', action='store_true', help='Discover latest PDFs only')
    group.add_argument('--export-only', action='store_true', help='Export existing queue to CSV')
    
    parser.add_argument('--end-year', type=int, help='End year for range discovery (required with --start-year)')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode (for debugging)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start_year and not args.end_year:
        parser.error("--end-year is required when using --start-year")
    
    if args.visible:
        args.headless = False
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize database
        db = CausaGanhaDB()
        
        # Export only mode
        if args.export_only:
            output_file = Path("data/tjro_pdf_discovery_queue.csv")
            await export_to_csv(db, output_file)
            return 0
        
        # Discovery mode
        start_time = datetime.now()
        
        async with TJROPlaywrightDiscovery(db, headless=args.headless) as discovery:
            
            if args.latest:
                results = await discovery.discover_latest()
            elif args.year:
                results = await discovery.discover_year(args.year)
            else:
                results = await discovery.discover_range(args.start_year, args.end_year)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Show results
            print(f"\n🎉 Discovery completed in {duration}")
            if isinstance(results, dict) and '_totals' in results:
                totals = results['_totals']
                print(f"📊 Total Results:")
                print(f"  Found: {totals['total']:,} PDFs")
                print(f"  New: {totals['new']:,}")
                print(f"  Existing: {totals['existing']:,}")
                print(f"  Errors: {totals['errors']:,}")
            else:
                print(f"📊 Results: {results}")
            
            # Export to CSV
            output_file = Path("data/tjro_pdf_discovery_queue.csv")
            await export_to_csv(db, output_file)
            
            print(f"\n📄 Data exported to: {output_file}")
            print(f"🔗 Next steps:")
            print(f"  1. Review the CSV file")
            print(f"  2. Commit the CSV to git")
            print(f"  3. Implement queue processors")
        
    except KeyboardInterrupt:
        logger.info("🛑 Discovery interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))