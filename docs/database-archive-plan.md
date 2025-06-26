# Database Archive Plan: Internet Archive Integration

**Status**: Planning Phase  
**Priority**: P1 (Enhancement)  
**Estimated Effort**: 2-3 days  
**Target**: Extend Internet Archive strategy to include DuckDB snapshots

## Overview

This plan extends CausaGanha's existing Internet Archive integration to include periodic database snapshots, providing public access to the complete TrueSkill ratings dataset and historical analysis capabilities.

## Current State

### ✅ **Already Implemented**
- PDF archival to Internet Archive with SHA-256 verification
- `pipeline/collect_and_archive.py` handles PDF uploads
- Metadata tracking in `pdfs` table
- Deduplication via hash comparison

### 🎯 **Gap Analysis**
- Database snapshots only stored in Cloudflare R2 (private)
- No public access to ratings data for transparency
- Limited historical analysis capabilities for researchers
- Missing long-term preservation strategy for ratings

## Proposed Solution

### **Three-Tier Database Archival Strategy**

#### **Tier 1: Real-time Operations (Current)**
- Local DuckDB: `data/causaganha.duckdb`
- Immediate access for daily pipeline operations
- Contains latest ratings, matches, and metadata

#### **Tier 2: Private Cloud Backup (Current)**
- Cloudflare R2: Compressed daily snapshots
- Cost-optimized storage with 30-day retention
- Remote analytics without downloads

#### **Tier 3: Public Archive (NEW)**
- Internet Archive: Weekly/monthly database snapshots
- Public transparency and research access
- Permanent preservation with global CDN

## Implementation Plan

### **Phase 1: Database Export Preparation**

#### 1.1 Enhanced Export Functionality
```python
# New methods in CausaGanhaDB class
def export_public_snapshot(self, output_path: Path) -> Dict[str, Any]:
    """Export anonymized database snapshot for public archive."""
    
def create_archive_metadata(self, snapshot_path: Path) -> Dict[str, str]:
    """Generate Internet Archive metadata for database snapshot."""
```

#### 1.2 Anonymization Layer
- **Lawyer names**: Replace with consistent hashes (e.g., `LAWYER_A1B2C3`)
- **Process numbers**: Keep format but anonymize digits
- **Dates**: Preserve year/month, anonymize specific days
- **Preserve**: TrueSkill ratings, match outcomes, statistical relationships

#### 1.3 Data Formats
- **Primary**: Compressed DuckDB file (`.duckdb.zst`)
- **Secondary**: CSV exports for broader compatibility
- **Metadata**: JSON with schema version, export date, record counts

### **Phase 2: Archive Integration**

#### 2.1 Internet Archive Configuration
```python
# New class in causaganha/core/archive_db.py
class DatabaseArchiver:
    def __init__(self, ia_config: IAConfig):
        self.ia_config = ia_config
        
    def create_database_item(self, snapshot_date: str) -> str:
        """Create IA item for database snapshot."""
        return f"causaganha-database-{snapshot_date}"
        
    def upload_database_snapshot(self, db_path: Path, metadata: Dict) -> bool:
        """Upload anonymized database to Internet Archive."""
```

#### 2.2 Archive Schedule
- **Weekly snapshots**: Every Sunday at 04:00 UTC
- **Monthly archives**: First Sunday of each month (retained permanently)
- **Quarterly releases**: Enhanced with analysis reports

#### 2.3 Item Naming Convention
```
Item ID: causaganha-database-YYYY-MM-DD
Title: CausaGanha TrueSkill Database - YYYY-MM-DD
Collection: opensource_data, legal_research
```

### **Phase 3: Workflow Integration**

#### 3.1 New GitHub Action: `database-archive.yml`
```yaml
name: Archive Database to Internet Archive

on:
  schedule:
    - cron: '0 4 * * 0' # Weekly on Sunday
  workflow_dispatch:
    inputs:
      force_monthly:
        description: 'Force monthly archive'
        type: boolean
        default: false

jobs:
  archive_database:
    runs-on: ubuntu-latest
    steps:
      - name: Export Anonymized Database
      - name: Compress and Validate
      - name: Upload to Internet Archive
      - name: Update Tracking Table
```

#### 3.2 Database Tracking Table
```sql
-- New table: archived_databases
CREATE TABLE IF NOT EXISTS archived_databases (
    id INTEGER PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    archive_type VARCHAR(20) CHECK (archive_type IN ('weekly', 'monthly', 'quarterly')),
    ia_identifier VARCHAR(100) NOT NULL UNIQUE,
    ia_url TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    sha256_hash CHAR(64) NOT NULL,
    total_lawyers INTEGER,
    total_matches INTEGER,
    total_decisions INTEGER,
    anonymization_version VARCHAR(10),
    upload_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Phase 4: Public Documentation**

#### 4.1 Archive Documentation
- **README file** for each archive item explaining data structure
- **Data dictionary** with field descriptions and relationships
- **Anonymization methodology** for transparency
- **Research guidelines** for academic use

#### 4.2 API Documentation
```markdown
# CausaGanha Database Archives

## Available Datasets
- Weekly snapshots: https://archive.org/download/causaganha-database-YYYY-MM-DD/
- Monthly archives: Permanent retention with enhanced metadata
- CSV exports: Compatible with Excel, R, Python pandas

## Data Structure
- `ratings.csv`: TrueSkill ratings (μ, σ, matches played)
- `matches.csv`: Match history with team compositions
- `metadata.json`: Export information and statistics
```

## Technical Specifications

### **File Structure**
```
causaganha-database-2025-06-30/
├── database.duckdb.zst          # Compressed DuckDB file
├── exports/
│   ├── ratings.csv             # Lawyer ratings
│   ├── matches.csv             # Match history  
│   ├── statistics.csv          # System statistics
│   └── metadata.json           # Export metadata
├── documentation/
│   ├── README.md              # Dataset overview
│   ├── schema.md              # Database schema
│   └── anonymization.md       # Privacy methodology
└── verification/
    ├── checksums.txt          # SHA-256 hashes
    └── export_log.txt         # Export process log
```

### **Anonymization Strategy**
- **Deterministic hashing**: Same lawyer always gets same hash
- **Format preservation**: Legal process numbers maintain structure
- **Statistical integrity**: All TrueSkill calculations remain valid
- **Reversibility**: Internal mapping for authorized research

### **Metadata Standards**
```json
{
  "identifier": "causaganha-database-2025-06-30",
  "title": "CausaGanha TrueSkill Database - June 30, 2025",
  "creator": "CausaGanha Project",
  "date": "2025-06-30",
  "description": "Anonymized judicial decision analysis using TrueSkill rating system",
  "subject": ["legal-analytics", "trueskill", "judicial-decisions", "rondonia"],
  "language": "por",
  "collection": ["opensource_data", "legal_research"],
  "licenseurl": "https://creativecommons.org/licenses/by/4.0/"
}
```

## Benefits

### **🔬 Research & Transparency**
- **Academic access**: Researchers can analyze judicial decision patterns
- **Public accountability**: Transparent lawyer performance data
- **Reproducible research**: Complete datasets with methodology
- **Historical analysis**: Long-term trends in judicial outcomes

### **📊 Data Preservation**
- **Permanent storage**: Internet Archive's mission of universal access
- **Multiple formats**: DuckDB + CSV for different use cases
- **Global access**: CDN ensures worldwide availability
- **Version control**: Complete history of database evolution

### **🏛️ Legal & Compliance**
- **Public data**: Based on already-public judicial decisions
- **Anonymization**: Protects individual privacy while preserving patterns
- **Transparency**: Open methodology and data processing
- **Academic standards**: Citable datasets with DOIs

## Implementation Timeline

### **Week 1: Core Development**
- [ ] Implement `DatabaseArchiver` class
- [ ] Add anonymization functions to `CausaGanhaDB`
- [ ] Create export and compression pipeline
- [ ] Add `archived_databases` table to migrations

### **Week 2: Archive Integration**
- [ ] Integrate with existing `ia` CLI tools
- [ ] Create `database-archive.yml` workflow
- [ ] Implement metadata generation
- [ ] Add error handling and validation

### **Week 3: Testing & Documentation**
- [ ] Test with staging Internet Archive account
- [ ] Generate sample datasets and documentation
- [ ] Validate anonymization effectiveness
- [ ] Performance testing with large datasets

### **Week 4: Production Deployment**
- [ ] Deploy to production with first weekly snapshot
- [ ] Monitor upload success and public accessibility
- [ ] Create public documentation and research guidelines
- [ ] Announce to legal research community

## Risk Assessment

### **🔒 Privacy & Security**
- **Risk**: Potential re-identification of anonymized data
- **Mitigation**: Rigorous anonymization testing, expert review
- **Monitoring**: Regular anonymization effectiveness audits

### **💾 Storage & Costs**
- **Risk**: Large database files consuming IA storage
- **Mitigation**: Compression, selective exports, retention policies
- **Monitoring**: File size trends and compression ratios

### **📡 Technical Reliability**
- **Risk**: Upload failures or corrupted archives
- **Mitigation**: SHA-256 verification, retry logic, validation
- **Monitoring**: Automated success/failure notifications

### **⚖️ Legal & Compliance**
- **Risk**: Potential legal challenges to data publication
- **Mitigation**: Legal review, compliance with transparency laws
- **Monitoring**: Regular legal compliance assessments

## Success Metrics

### **📈 Quantitative**
- **Archive completeness**: 100% of scheduled snapshots uploaded successfully
- **Download activity**: Tracking research and public interest
- **Data integrity**: Zero corruption incidents, 100% hash verification
- **Performance**: Upload times < 30 minutes, compression ratios > 80%

### **🎯 Qualitative**
- **Research adoption**: Academic papers using CausaGanha datasets
- **Community feedback**: Positive reception from legal research community
- **Transparency impact**: Enhanced public trust in judicial system
- **System reliability**: Robust, automated archive process

## Future Enhancements

### **🚀 Advanced Features**
- **Interactive dashboards**: Public analytics interface
- **API access**: Programmatic data access for researchers
- **Collaborative analysis**: Community-contributed insights
- **Machine learning datasets**: Pre-processed data for ML research

### **🔗 Integration Opportunities**
- **Academic partnerships**: University research collaborations
- **Open data initiatives**: Integration with government transparency efforts
- **Legal technology**: APIs for legal tech companies
- **International expansion**: Template for other judicial systems

---

**Next Steps**: Review plan with stakeholders, prioritize implementation phases, and begin core development for Phase 1.