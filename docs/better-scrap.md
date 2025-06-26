# Enhanced TJRO PDF Collection Strategy

**Status**: Ready for Implementation  
**Priority**: P2 (High Value)  
**Estimated Effort**: 3-5 days  
**Target**: Build resilient, production-grade PDF collection system

## Executive Summary

Transform the current fragile PDF collection into a robust, self-healing system that can handle TJRO website changes, network failures, and unexpected issues without manual intervention.

## Current State Analysis

### 🔴 **Critical Issues**

1. **Single Point of Failure**: One URL pattern breaks → entire pipeline stops
2. **No Resilience**: Network timeouts cause immediate failure
3. **Zero Observability**: No metrics on success rates or failure patterns
4. **Manual Recovery**: Failures require human debugging and intervention
5. **Rigid Implementation**: Hard-coded URL patterns in `src/downloader.py`

### 📊 **Impact Assessment**

- **Current Success Rate**: ~85% (estimated from recent runs)
- **Recovery Time**: 2-4 hours (manual intervention required)
- **Data Loss Risk**: High (missed days require manual collection)

## Proposed Solution Architecture

### 🎯 **Core Design Principles**

1. **Fail-Safe**: Multiple collection strategies with automatic fallback
2. **Self-Healing**: Automatic retry with intelligent backoff
3. **Observable**: Comprehensive logging and metrics
4. **Maintainable**: Clear separation of concerns and extensible design

### 🏗️ **Technical Architecture**

```python
# src/collectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

@dataclass
class CollectionResult:
    success: bool
    pdf_path: Optional[Path]
    strategy_used: str
    attempts: int
    error_message: Optional[str]
    metadata: dict

class PDFCollectionStrategy(ABC):
    @abstractmethod
    def collect(self, date: str, output_dir: Path) -> CollectionResult:
        pass
    
    @abstractmethod
    def can_handle(self, date: str) -> bool:
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        pass

# src/collectors/tjro_collector.py
class RobustTJROCollector:
    def __init__(self):
        self.strategies = self._load_strategies()
        self.metrics = CollectionMetrics()
        
    def _load_strategies(self) -> List[PDFCollectionStrategy]:
        return sorted([
            DirectURLStrategy(),           # Priority 1: Current approach (enhanced)
            SearchBasedStrategy(),         # Priority 2: Navigate search pages
            ArchiveRedirectStrategy(),     # Priority 3: Follow redirect chains
            CachedMirrorStrategy(),        # Priority 4: Known mirror sites
        ], key=lambda s: s.priority)
    
    def collect_pdf(self, date: str, output_dir: Path = None) -> CollectionResult:
        """Collect PDF using multiple strategies with fallback."""
        output_dir = output_dir or Path("data")
        
        for strategy in self.strategies:
            if not strategy.can_handle(date):
                continue
                
            try:
                result = self._attempt_with_strategy(strategy, date, output_dir)
                if result.success:
                    self.metrics.record_success(strategy.__class__.__name__)
                    return result
                else:
                    self.metrics.record_failure(strategy.__class__.__name__, result.error_message)
                    
            except Exception as e:
                self.metrics.record_failure(strategy.__class__.__name__, str(e))
                continue
        
        # All strategies failed
        self.metrics.record_total_failure(date)
        return CollectionResult(
            success=False,
            pdf_path=None,
            strategy_used="none",
            attempts=len(self.strategies),
            error_message="All collection strategies failed",
            metadata={"date": date}
        )
```

## Implementation Plan

### **Phase 1: Foundation (Days 1-2)**

#### 1.1 Create Strategy Framework
```bash
mkdir -p src/collectors
touch src/collectors/__init__.py
touch src/collectors/base.py
touch src/collectors/tjro_collector.py
touch src/collectors/metrics.py
```

#### 1.2 Enhanced Direct URL Strategy
```python
# src/collectors/strategies/direct_url.py
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urljoin

class DirectURLStrategy(PDFCollectionStrategy):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True
    )
    def collect(self, date: str, output_dir: Path) -> CollectionResult:
        """Enhanced version of current approach with retries."""
        try:
            # Multiple URL patterns to try
            url_patterns = [
                f"https://www.tjro.jus.br/images/stories/diarios/{date.replace('-', '')}/dj_{date.replace('-', '')}.pdf",
                f"https://tjro.jus.br/images/diarios/{date}/dj_{date.replace('-', '')}.pdf",
                # Add more patterns as discovered
            ]
            
            for url in url_patterns:
                response = self.session.get(url, timeout=30, stream=True)
                if response.status_code == 200:
                    # Validate PDF content
                    if self._is_valid_pdf(response):
                        pdf_path = self._save_pdf(response, date, output_dir)
                        return CollectionResult(
                            success=True,
                            pdf_path=pdf_path,
                            strategy_used="direct_url",
                            attempts=1,
                            error_message=None,
                            metadata={"url": url, "size": len(response.content)}
                        )
            
            return CollectionResult(
                success=False,
                pdf_path=None,
                strategy_used="direct_url",
                attempts=len(url_patterns),
                error_message="No valid PDF found at known URLs",
                metadata={"urls_tried": url_patterns}
            )
            
        except Exception as e:
            raise CollectionException(f"Direct URL strategy failed: {e}")
```

#### 1.3 Metrics and Monitoring
```python
# src/collectors/metrics.py
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass, field

@dataclass
class CollectionMetrics:
    success_count: int = 0
    failure_count: int = 0
    strategy_stats: Dict[str, Dict] = field(default_factory=dict)
    recent_failures: List[str] = field(default_factory=list)
    
    def record_success(self, strategy: str):
        self.success_count += 1
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {"success": 0, "failure": 0}
        self.strategy_stats[strategy]["success"] += 1
        
    def record_failure(self, strategy: str, error: str):
        self.failure_count += 1
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {"success": 0, "failure": 0}
        self.strategy_stats[strategy]["failure"] += 1
        self.recent_failures.append(f"{datetime.now()}: {strategy} - {error}")
        
    def get_success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
        
    def should_alert(self) -> bool:
        """Alert if success rate drops below 70% or 3+ consecutive failures."""
        return (
            self.get_success_rate() < 0.7 or 
            len(self.recent_failures) >= 3
        )
```

### **Phase 2: Search-Based Fallback (Day 3)**

#### 2.1 Search Strategy Implementation
```python
# src/collectors/strategies/search_based.py
class SearchBasedStrategy(PDFCollectionStrategy):
    def collect(self, date: str, output_dir: Path) -> CollectionResult:
        """Navigate TJRO search pages to find PDF."""
        try:
            # 1. Go to TJRO main page
            main_page = self.session.get("https://www.tjro.jus.br")
            
            # 2. Find search or "Diários" section
            soup = BeautifulSoup(main_page.content, 'html.parser')
            search_links = self._find_diary_links(soup)
            
            # 3. Navigate to date-specific pages
            for link in search_links:
                pdf_url = self._search_for_date(link, date)
                if pdf_url:
                    return self._download_from_url(pdf_url, date, output_dir)
                    
            return CollectionResult(success=False, ...)
            
        except Exception as e:
            raise CollectionException(f"Search strategy failed: {e}")
    
    def _find_diary_links(self, soup) -> List[str]:
        """Extract diary/diário related links from main page."""
        keywords = ["diário", "diarios", "diary", "publicações"]
        links = []
        for keyword in keywords:
            elements = soup.find_all('a', href=True, string=re.compile(keyword, re.I))
            links.extend([elem['href'] for elem in elements])
        return links
```

#### 2.2 Archive Redirect Strategy
```python
# src/collectors/strategies/archive_redirect.py
class ArchiveRedirectStrategy(PDFCollectionStrategy):
    def collect(self, date: str, output_dir: Path) -> CollectionResult:
        """Follow redirect chains to find current PDF location."""
        try:
            # Start with known old URLs and follow redirects
            old_patterns = [
                f"https://old.tjro.jus.br/diarios/{date}/",
                f"https://www.tjro.jus.br/legacy/diarios/{date.replace('-', '')}/",
                # Add more historical patterns
            ]
            
            for base_url in old_patterns:
                final_url = self._follow_redirects(base_url)
                if final_url and self._looks_like_pdf_url(final_url):
                    return self._download_from_url(final_url, date, output_dir)
                    
            return CollectionResult(success=False, ...)
            
        except Exception as e:
            raise CollectionException(f"Archive redirect strategy failed: {e}")
```

### **Phase 3: Integration and Testing (Day 4)**

#### 3.1 Update Main Downloader
```python
# src/downloader.py (updated)
from src.collectors.tjro_collector import RobustTJROCollector

def fetch_tjro_pdf(date_obj: date, output_dir: Path = None) -> Optional[Path]:
    """Enhanced PDF collection with multiple strategies."""
    collector = RobustTJROCollector()
    result = collector.collect_pdf(date_obj.strftime('%Y-%m-%d'), output_dir)
    
    if result.success:
        logger.info(f"PDF collected successfully using {result.strategy_used}")
        return result.pdf_path
    else:
        logger.error(f"All collection strategies failed: {result.error_message}")
        return None

def fetch_latest_tjro_pdf(output_dir: Path = None) -> Optional[Path]:
    """Get latest PDF with enhanced collection."""
    yesterday = datetime.now().date() - timedelta(days=1)
    return fetch_tjro_pdf(yesterday, output_dir)
```

#### 3.2 CLI Integration
```python
# src/cli.py (enhanced)
def handle_download_command(args):
    """Enhanced download with strategy reporting."""
    collector = RobustTJROCollector()
    
    if args.latest:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        date = args.date
        
    result = collector.collect_pdf(date)
    
    if result.success:
        print(f"✅ PDF downloaded: {result.pdf_path}")
        print(f"Strategy used: {result.strategy_used}")
        print(f"Attempts: {result.attempts}")
    else:
        print(f"❌ Collection failed: {result.error_message}")
        print(f"Strategies tried: {result.attempts}")
        
    # Show metrics
    metrics = collector.metrics
    print(f"\n📊 Collection Stats:")
    print(f"Success rate: {metrics.get_success_rate():.1%}")
    print(f"Total attempts: {metrics.success_count + metrics.failure_count}")
```

### **Phase 4: Monitoring and Alerting (Day 5)**

#### 4.1 Health Check Endpoint
```python
# src/health.py
class CollectionHealthChecker:
    def __init__(self):
        self.collector = RobustTJROCollector()
        
    def run_health_check(self) -> Dict:
        """Test all strategies with a recent date."""
        test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        results = {}
        for strategy in self.collector.strategies:
            try:
                result = strategy.collect(test_date, Path("/tmp"))
                results[strategy.__class__.__name__] = {
                    "status": "healthy" if result.success else "unhealthy",
                    "error": result.error_message
                }
            except Exception as e:
                results[strategy.__class__.__name__] = {
                    "status": "error",
                    "error": str(e)
                }
                
        return {
            "overall_health": "healthy" if any(r["status"] == "healthy" for r in results.values()) else "unhealthy",
            "strategies": results,
            "timestamp": datetime.now().isoformat()
        }
```

#### 4.2 GitHub Actions Integration
```yaml
# .github/workflows/collection-health.yml
name: Collection Health Check

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  health_check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup
      
      - name: Run health check
        run: |
          uv run python -c "
          from src.health import CollectionHealthChecker
          import json
          
          checker = CollectionHealthChecker()
          health = checker.run_health_check()
          
          print(json.dumps(health, indent=2))
          
          # Fail if unhealthy
          if health['overall_health'] == 'unhealthy':
              exit(1)
          "
      
      - name: Create issue on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'PDF Collection Health Check Failed',
              body: 'The PDF collection system health check failed. Please investigate.',
              labels: ['bug', 'collection-failure']
            })
```

## Testing Strategy

### Unit Tests
```python
# tests/test_collectors.py
class TestTJROCollector:
    def test_direct_url_strategy_success(self):
        # Mock successful PDF download
        pass
        
    def test_fallback_on_strategy_failure(self):
        # Test that fallback strategies are tried
        pass
        
    def test_metrics_tracking(self):
        # Verify metrics are recorded correctly
        pass
```

### Integration Tests
```python
# tests/test_collection_integration.py
class TestCollectionIntegration:
    def test_end_to_end_collection(self):
        # Test full collection process
        pass
        
    def test_all_strategies_fail_gracefully(self):
        # Test behavior when all strategies fail
        pass
```

## Expected Benefits

### 📈 **Reliability Improvements**
- **Success Rate**: 85% → 95% (estimated)
- **Recovery Time**: 2-4 hours → 5-10 minutes (automatic)
- **Manual Intervention**: Daily → Weekly/Monthly

### 🔍 **Observability**
- Real-time success/failure metrics
- Strategy performance tracking
- Automated health checks
- Proactive failure alerting

### 🛠️ **Maintainability**
- Clear separation of collection strategies
- Easy to add new collection methods
- Comprehensive logging for debugging
- Automated testing of collection methods

## Risk Assessment

### **Low Risk**
- **Backward Compatibility**: Enhanced system wraps existing downloader.py
- **Gradual Rollout**: Can be deployed as opt-in feature initially
- **Fallback**: Current system remains as primary strategy

### **Mitigations**
- **Testing**: Comprehensive test suite with mocked responses
- **Monitoring**: Health checks catch issues early
- **Documentation**: Clear troubleshooting guides

## Success Metrics

1. **Collection Success Rate** > 95%
2. **Time to Recovery** < 10 minutes
3. **Manual Interventions** < 1 per week
4. **False Positive Alerts** < 5%

---

**Ready for Implementation**: This plan provides concrete, actionable steps to build a production-grade PDF collection system that can handle real-world challenges reliably.