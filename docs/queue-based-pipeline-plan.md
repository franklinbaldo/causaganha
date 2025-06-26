# Queue-Based Pipeline Architecture Plan

**Status**: Ready for Implementation  
**Priority**: P1 (High Impact)  
**Estimated Effort**: 5-7 days  
**Target**: Build scalable, fault-tolerant pipeline with queue-based processing

## Executive Summary

Transform CausaGanha from a linear pipeline to a robust, queue-based system that can handle failures gracefully, process PDFs in parallel, and maintain data consistency across all stages.

## Current vs Proposed Architecture

### 🔴 **Current Linear Pipeline**
```
Download → Archive → Extract → Update Ratings
   ↓         ↓         ↓           ↓
 FAIL     FAIL      FAIL        FAIL
   ↓         ↓         ↓           ↓
Manual   Manual    Manual      Manual
```

### ✅ **Proposed Queue-Based Pipeline**
```
PDF URLs → [Queue 1: Archive] → [Queue 2: Extract] → [Queue 3: Process Ratings]
    ↓            ↓                    ↓                      ↓
Discovery     Archive to IA       Gemini Analysis      TrueSkill Updates
Queue         Queue               Queue                Queue
    ↓            ↓                    ↓                      ↓
Automatic     Automatic           Automatic            Automatic
Retry         Retry               Retry                Retry
```

## Database Schema Design

### Queue Tables
```sql
-- migrations/003_queue_system.sql
CREATE TABLE pdf_discovery_queue (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL,
    date TEXT NOT NULL,
    number TEXT,  -- e.g., "249", "249S"
    year INTEGER NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,  -- Higher numbers = higher priority
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    metadata JSON,  -- Store additional info from TJRO API
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pdf_archive_queue (
    id INTEGER PRIMARY KEY,
    pdf_id INTEGER REFERENCES pdfs(id),
    local_path TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    ia_url TEXT,  -- Internet Archive URL after successful upload
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pdf_extraction_queue (
    id INTEGER PRIMARY KEY,
    pdf_id INTEGER REFERENCES pdfs(id),
    local_path TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    extraction_result JSON,  -- Store Gemini response
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rating_processing_queue (
    id INTEGER PRIMARY KEY,
    pdf_id INTEGER REFERENCES pdfs(id),
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    error_message TEXT,
    decisions_processed INTEGER DEFAULT 0,
    ratings_updated INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced PDFs table
ALTER TABLE pdfs ADD COLUMN discovery_queue_id INTEGER REFERENCES pdf_discovery_queue(id);
ALTER TABLE pdfs ADD COLUMN file_size INTEGER;
ALTER TABLE pdfs ADD COLUMN download_duration_ms INTEGER;

-- Indexes for performance
CREATE INDEX idx_discovery_queue_status_priority ON pdf_discovery_queue(status, priority DESC);
CREATE INDEX idx_archive_queue_status ON pdf_archive_queue(status);
CREATE INDEX idx_extraction_queue_status ON pdf_extraction_queue(status);
CREATE INDEX idx_rating_queue_status ON rating_processing_queue(status);
```

## Implementation Architecture

### 🏗️ **Core Queue System**

```python
# src/queues/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

@dataclass
class QueueItem:
    id: int
    status: str
    attempts: int
    last_attempt: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]

class QueueProcessor(ABC):
    def __init__(self, db: 'CausaGanhaDB', max_attempts: int = 3):
        self.db = db
        self.max_attempts = max_attempts
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def process_item(self, item: QueueItem) -> bool:
        """Process a single queue item. Return True if successful."""
        pass
    
    @abstractmethod
    def get_pending_items(self, limit: int = 10) -> List[QueueItem]:
        """Get pending items from the queue."""
        pass
    
    @abstractmethod
    def update_item_status(self, item_id: int, status: str, error: str = None):
        """Update item status in the queue."""
        pass
    
    def run_batch(self, batch_size: int = 10) -> Dict[str, int]:
        """Process a batch of items from the queue."""
        items = self.get_pending_items(batch_size)
        results = {"processed": 0, "succeeded": 0, "failed": 0}
        
        for item in items:
            results["processed"] += 1
            
            try:
                self.update_item_status(item.id, "processing")
                success = self.process_item(item)
                
                if success:
                    self.update_item_status(item.id, "completed")
                    results["succeeded"] += 1
                    self.logger.info(f"Successfully processed item {item.id}")
                else:
                    self._handle_failure(item)
                    results["failed"] += 1
                    
            except Exception as e:
                self.logger.error(f"Error processing item {item.id}: {e}")
                self._handle_failure(item, str(e))
                results["failed"] += 1
                
        return results
    
    def _handle_failure(self, item: QueueItem, error: str = None):
        """Handle failed item processing."""
        if item.attempts >= self.max_attempts:
            self.update_item_status(item.id, "failed", error)
            self.logger.error(f"Item {item.id} failed permanently after {item.attempts} attempts")
        else:
            self.update_item_status(item.id, "pending", error)
            self.logger.warning(f"Item {item.id} failed, will retry (attempt {item.attempts + 1})")
```

### **Phase 1: PDF Discovery Queue**

```python
# src/queues/discovery.py
import requests
from datetime import datetime, timedelta
from typing import List, Dict

class PDFDiscoveryProcessor(QueueProcessor):
    def __init__(self, db):
        super().__init__(db)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; CausaGanha/1.0)'
        })
    
    def discover_pdfs_for_year(self, year: int) -> int:
        """Discover all PDFs for a given year and add to queue."""
        try:
            url = f"https://www.tjro.jus.br/diario_oficial/list.php?ano={year}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            pdfs_data = response.json()
            added_count = 0
            
            for pdf_info in pdfs_data:
                if not self._is_already_queued(pdf_info):
                    self._add_to_discovery_queue(pdf_info)
                    added_count += 1
                    
            return added_count
            
        except Exception as e:
            self.logger.error(f"Failed to discover PDFs for year {year}: {e}")
            raise
    
    def discover_latest_pdfs(self) -> int:
        """Discover latest PDFs and add to queue."""
        try:
            url = "https://www.tjro.jus.br/diario_oficial/data-ultimo-diario.php"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            latest_pdfs = response.json()
            added_count = 0
            
            for pdf_info in latest_pdfs:
                if not self._is_already_queued(pdf_info):
                    self._add_to_discovery_queue(pdf_info, priority=10)  # High priority
                    added_count += 1
                    
            return added_count
            
        except Exception as e:
            self.logger.error(f"Failed to discover latest PDFs: {e}")
            raise
    
    def process_item(self, item: QueueItem) -> bool:
        """Download PDF and move to archive queue."""
        try:
            pdf_url = item.metadata.get('url')
            date_str = item.metadata.get('date')
            
            # Download PDF
            response = self.session.get(pdf_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Validate PDF content
            if not self._is_valid_pdf(response):
                raise ValueError("Downloaded content is not a valid PDF")
            
            # Save to local storage
            local_path = self._save_pdf(response, date_str)
            
            # Create PDF record in database
            pdf_id = self.db.create_pdf_record({
                'url': pdf_url,
                'date': date_str,
                'local_path': str(local_path),
                'file_size': len(response.content),
                'discovery_queue_id': item.id,
                'sha256_hash': self._calculate_hash(response.content)
            })
            
            # Add to archive queue
            self.db.add_to_archive_queue(pdf_id, local_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process discovery item {item.id}: {e}")
            return False
    
    def _add_to_discovery_queue(self, pdf_info: Dict, priority: int = 0):
        """Add PDF info to discovery queue."""
        self.db.execute("""
            INSERT INTO pdf_discovery_queue (url, date, number, year, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pdf_info['url'],
            f"{pdf_info['year']}-{pdf_info['month']:02d}-{pdf_info['day']:02d}",
            pdf_info.get('number'),
            int(pdf_info['year']),
            priority,
            json.dumps(pdf_info)
        ))
```

### **Phase 2: Archive Queue Processor**

```python
# src/queues/archive.py
import subprocess
from pathlib import Path

class PDFArchiveProcessor(QueueProcessor):
    def __init__(self, db):
        super().__init__(db)
        self.ia_config = self._load_ia_config()
    
    def process_item(self, item: QueueItem) -> bool:
        """Archive PDF to Internet Archive."""
        try:
            pdf_record = self.db.get_pdf_by_id(item.metadata['pdf_id'])
            local_path = Path(pdf_record['local_path'])
            
            if not local_path.exists():
                raise FileNotFoundError(f"PDF file not found: {local_path}")
            
            # Create Internet Archive item
            ia_item_id = self._create_ia_item_id(pdf_record)
            
            # Check if already exists
            if self._ia_item_exists(ia_item_id):
                self.logger.info(f"PDF already exists in IA: {ia_item_id}")
                ia_url = f"https://archive.org/details/{ia_item_id}"
            else:
                # Upload to Internet Archive
                ia_url = self._upload_to_ia(local_path, ia_item_id, pdf_record)
            
            # Update PDF record with IA URL
            self.db.update_pdf_record(pdf_record['id'], {'ia_url': ia_url})
            
            # Add to extraction queue
            self.db.add_to_extraction_queue(pdf_record['id'], local_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to archive PDF {item.id}: {e}")
            return False
    
    def _upload_to_ia(self, local_path: Path, item_id: str, pdf_record: Dict) -> str:
        """Upload PDF to Internet Archive using ia CLI."""
        try:
            metadata = {
                'title': f"Diário de Justiça RO - {pdf_record['date']}",
                'description': f"Diário Oficial de Justiça de Rondônia do dia {pdf_record['date']}",
                'creator': 'Tribunal de Justiça de Rondônia',
                'date': pdf_record['date'],
                'collection': 'opensource',
                'mediatype': 'texts',
                'subject': ['law', 'brazil', 'rondonia', 'justice', 'oficial-diary']
            }
            
            # Build ia command
            cmd = ['ia', 'upload', item_id, str(local_path)]
            for key, value in metadata.items():
                if isinstance(value, list):
                    for v in value:
                        cmd.extend([f'--metadata={key}:{v}'])
                else:
                    cmd.extend([f'--metadata={key}:{value}'])
            
            # Execute upload
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
            
            return f"https://archive.org/details/{item_id}"
            
        except Exception as e:
            self.logger.error(f"IA upload failed: {e}")
            raise
```

### **Phase 3: Extraction Queue Processor**

```python
# src/queues/extraction.py
import google.generativeai as genai
from pathlib import Path
import json

class PDFExtractionProcessor(QueueProcessor):
    def __init__(self, db):
        super().__init__(db, max_attempts=2)  # Gemini is expensive, fewer retries
        self.setup_gemini()
    
    def process_item(self, item: QueueItem) -> bool:
        """Extract content from PDF using Gemini."""
        try:
            pdf_record = self.db.get_pdf_by_id(item.metadata['pdf_id'])
            local_path = Path(pdf_record['local_path'])
            
            if not local_path.exists():
                raise FileNotFoundError(f"PDF file not found: {local_path}")
            
            # Extract content using Gemini
            extraction_result = self._extract_with_gemini(local_path)
            
            # Validate extraction result
            if not self._is_valid_extraction(extraction_result):
                raise ValueError("Gemini extraction returned invalid data")
            
            # Store extracted decisions in database
            decisions_count = self._store_decisions(pdf_record['id'], extraction_result)
            
            # Add to rating processing queue
            if decisions_count > 0:
                self.db.add_to_rating_queue(pdf_record['id'])
            
            # Update extraction queue with result
            self.db.execute("""
                UPDATE pdf_extraction_queue 
                SET extraction_result = ? 
                WHERE id = ?
            """, (json.dumps(extraction_result), item.id))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF {item.id}: {e}")
            return False
    
    def _extract_with_gemini(self, pdf_path: Path) -> Dict:
        """Extract decisions from PDF using Gemini."""
        # Use existing extraction logic from extractor.py
        # but adapted for queue processing
        from src.extractor import GeminiExtractor
        
        extractor = GeminiExtractor()
        return extractor.extract_decisions_from_pdf(pdf_path)
    
    def _store_decisions(self, pdf_id: int, extraction_result: Dict) -> int:
        """Store extracted decisions in database."""
        decisions = extraction_result.get('decisions', [])
        stored_count = 0
        
        for decision in decisions:
            try:
                self.db.insert_decision({
                    'pdf_id': pdf_id,
                    'process_number': decision.get('process_number'),
                    'polo_ativo': decision.get('polo_ativo'),
                    'polo_passivo': decision.get('polo_passivo'),
                    'lawyers_polo_ativo': decision.get('lawyers_polo_ativo', []),
                    'lawyers_polo_passivo': decision.get('lawyers_polo_passivo', []),
                    'decision_type': decision.get('decision_type'),
                    'outcome': decision.get('outcome'),
                    'summary': decision.get('summary'),
                    'raw_text': decision.get('raw_text')
                })
                stored_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to store decision: {e}")
                
        return stored_count
```

### **Phase 4: Rating Processing Queue**

```python
# src/queues/ratings.py
from src.trueskill_rating import TrueSkillRatingSystem

class RatingProcessingProcessor(QueueProcessor):
    def __init__(self, db):
        super().__init__(db)
        self.rating_system = TrueSkillRatingSystem(db)
    
    def process_item(self, item: QueueItem) -> bool:
        """Process TrueSkill ratings for decisions from a PDF."""
        try:
            pdf_id = item.metadata['pdf_id']
            
            # Get all decisions for this PDF
            decisions = self.db.get_decisions_by_pdf_id(pdf_id)
            
            if not decisions:
                self.logger.warning(f"No decisions found for PDF {pdf_id}")
                return True
            
            processed_count = 0
            updated_ratings = 0
            
            for decision in decisions:
                try:
                    # Process TrueSkill rating for this decision
                    if self.rating_system.process_decision(decision):
                        updated_ratings += 1
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process decision {decision['id']}: {e}")
            
            # Update queue item with statistics
            self.db.execute("""
                UPDATE rating_processing_queue 
                SET decisions_processed = ?, ratings_updated = ? 
                WHERE id = ?
            """, (processed_count, updated_ratings, item.id))
            
            self.logger.info(f"Processed {processed_count} decisions, updated {updated_ratings} ratings for PDF {pdf_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process ratings for item {item.id}: {e}")
            return False
```

## CLI Integration

```python
# src/cli.py (enhanced with queue commands)
def handle_queue_command(args):
    """Handle queue-related commands."""
    db = CausaGanhaDB()
    
    if args.action == 'discover':
        # Discover PDFs and add to queue
        processor = PDFDiscoveryProcessor(db)
        
        if args.year:
            count = processor.discover_pdfs_for_year(args.year)
            print(f"✅ Discovered {count} PDFs for year {args.year}")
        elif args.latest:
            count = processor.discover_latest_pdfs()
            print(f"✅ Discovered {count} latest PDFs")
        else:
            # Discover recent years
            current_year = datetime.now().year
            total_count = 0
            for year in range(current_year - 1, current_year + 1):
                count = processor.discover_pdfs_for_year(year)
                total_count += count
                print(f"✅ Discovered {count} PDFs for year {year}")
            print(f"🎯 Total: {total_count} PDFs discovered")
    
    elif args.action == 'process':
        # Process queues
        processors = {
            'discovery': PDFDiscoveryProcessor(db),
            'archive': PDFArchiveProcessor(db),
            'extraction': PDFExtractionProcessor(db),
            'ratings': RatingProcessingProcessor(db)
        }
        
        queue_type = args.queue_type or 'all'
        batch_size = args.batch_size or 10
        
        if queue_type == 'all':
            total_results = {}
            for name, processor in processors.items():
                results = processor.run_batch(batch_size)
                total_results[name] = results
                print(f"📊 {name.title()}: {results}")
        else:
            processor = processors.get(queue_type)
            if processor:
                results = processor.run_batch(batch_size)
                print(f"📊 {queue_type.title()}: {results}")
            else:
                print(f"❌ Unknown queue type: {queue_type}")
    
    elif args.action == 'status':
        # Show queue status
        status = db.get_queue_status()
        print("📊 Queue Status:")
        for queue_name, stats in status.items():
            print(f"  {queue_name}: {stats}")

# Add queue subcommand to main CLI
queue_parser = subparsers.add_parser('queue', help='Queue operations')
queue_parser.add_argument('action', choices=['discover', 'process', 'status'])
queue_parser.add_argument('--year', type=int, help='Year to discover PDFs for')
queue_parser.add_argument('--latest', action='store_true', help='Discover latest PDFs')
queue_parser.add_argument('--queue-type', choices=['discovery', 'archive', 'extraction', 'ratings'], help='Queue type to process')
queue_parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
```

## Usage Examples

```bash
# Discovery phase - populate the pipeline
causaganha queue discover --year 2024     # Discover all 2024 PDFs
causaganha queue discover --latest        # Discover latest PDFs
causaganha queue discover                  # Discover recent years

# Processing phase - run the pipeline
causaganha queue process --queue-type discovery --batch-size 5
causaganha queue process --queue-type archive --batch-size 3
causaganha queue process --queue-type extraction --batch-size 2
causaganha queue process --queue-type ratings --batch-size 10
causaganha queue process                   # Process all queues

# Monitoring
causaganha queue status                    # Show queue statistics

# Automated processing (for cron/GitHub Actions)
causaganha queue discover --latest && \
causaganha queue process --batch-size 5
```

## Expected Benefits

### 🎯 **Reliability & Scalability**
- **Fault Tolerance**: Failed items retry automatically
- **Parallel Processing**: Multiple PDFs processed simultaneously
- **Graceful Degradation**: System continues working even if one stage fails
- **Backpressure Handling**: Queues prevent system overload

### 📊 **Observability & Control**
- **Queue Monitoring**: Real-time visibility into processing status
- **Retry Logic**: Automatic retry with exponential backoff
- **Progress Tracking**: See exactly which PDFs are in which stage
- **Batch Processing**: Control resource usage with configurable batch sizes

### 🔧 **Operational Excellence**
- **Resume Processing**: Restart from where it left off after failures
- **Priority Handling**: Process urgent items first
- **Resource Management**: Control Gemini API usage and costs
- **Historical Processing**: Easily process older PDFs

### 💰 **Cost Optimization**
- **Efficient API Usage**: Only call Gemini for new PDFs
- **Deduplication**: Avoid processing same PDF multiple times
- **Batch Processing**: Optimize database operations
- **Smart Retry**: Avoid unnecessary API calls

## Implementation Timeline

### **Day 1-2: Database Schema & Base Classes**
- Create queue tables and indexes
- Implement base QueueProcessor class
- Set up database methods for queue operations

### **Day 3: Discovery Queue**
- Implement PDFDiscoveryProcessor
- Add CLI commands for PDF discovery
- Test with recent PDFs

### **Day 4: Archive Queue**
- Implement PDFArchiveProcessor
- Integrate with Internet Archive
- Test end-to-end discovery → archive

### **Day 5: Extraction Queue**
- Implement PDFExtractionProcessor
- Integrate with existing Gemini extraction
- Test full pipeline through extraction

### **Day 6: Rating Queue**
- Implement RatingProcessingProcessor
- Integrate with TrueSkill system
- Test complete pipeline

### **Day 7: Integration & Monitoring**
- Add comprehensive logging and metrics
- Create GitHub Actions for automated processing
- Performance testing and optimization

---

**This queue-based architecture transforms CausaGanha into a resilient, scalable system that can handle the full lifecycle of PDF processing with automatic error recovery and parallel processing capabilities.**