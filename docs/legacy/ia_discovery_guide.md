# Internet Archive Discovery Guide

## 🔍 **How to List and Discover Uploaded TJRO Diarios**

Once your TJRO diarios are uploaded to Internet Archive, there are multiple ways to discover, list, and access them systematically.

---

## **1. Programmatic Discovery (Our Tools)**

### **A. Search by Year**

```bash
# Find all 2025 diarios
uv run python src/ia_discovery.py --year 2025

# Find all 2024 diarios
uv run python src/ia_discovery.py --year 2024
```

### **B. Search by Date Range**

```bash
# Find diarios in specific date range
uv run python src/ia_discovery.py --start-date 2024-01-01 --end-date 2024-12-31

# Find recent diarios
uv run python src/ia_discovery.py --start-date 2025-06-01 --end-date 2025-06-26
```

### **C. Coverage Analysis**

```bash
# Check what's missing vs what should be there
uv run python src/ia_discovery.py --coverage-report --year 2025

# Full coverage report across all years
uv run python src/ia_discovery.py --coverage-report
```

### **D. Export Inventory**

```bash
# Export complete inventory to JSON
uv run python src/ia_discovery.py --export ia_inventory_2025.json --year 2025

# Export all diarios
uv run python src/ia_discovery.py --export ia_complete_inventory.json
```

### **E. Check Specific Items**

```bash
# Check if specific identifier exists
uv run python src/ia_discovery.py --check-identifier "tjro-diario-2025-06-26"
```

---

## **2. Internet Archive Web Interface**

### **A. Direct Search URL**

```
https://archive.org/search.php?query=creator%3A%22Tribunal%20de%20Justi%C3%A7a%20de%20Rond%C3%B4nia%22
```

### **B. Advanced Search**

1. Go to https://archive.org/advancedsearch.php
2. Enter search criteria:
   - **Creator**: `Tribunal de Justiça de Rondônia`
   - **Title**: `Diário da Justiça TJRO`
   - **Date Range**: `2025-01-01 to 2025-12-31` (adjust as needed)
   - **Media Type**: `texts`

### **C. Collection Browsing**

- Browse the `opensource` collection: https://archive.org/details/opensource
- Filter by creator or title

---

## **3. Internet Archive API**

### **A. Search API**

```bash
# Direct API call
curl "https://archive.org/advancedsearch.php?q=creator:\"Tribunal de Justiça de Rondônia\"&fl=identifier,title,date&output=json"
```

### **B. Metadata API**

```bash
# Get detailed metadata for specific item
curl "https://archive.org/metadata/tjro-diario-2025-06-26"
```

### **C. Python Requests**

```python
import requests

# Search for diarios
response = requests.get(
    "https://archive.org/advancedsearch.php",
    params={
        'q': 'creator:"Tribunal de Justiça de Rondônia"',
        'fl': 'identifier,title,date,downloads',
        'sort': 'date desc',
        'output': 'json',
        'rows': 1000
    }
)

items = response.json()['response']['docs']
for item in items:
    print(f"{item['identifier']}: {item['title']}")
```

---

## **4. Identifier Patterns**

Our diarios follow predictable identifier patterns:

### **A. Standard Format**

```
tjro-diario-YYYY-MM-DD
```

**Examples:**

- `tjro-diario-2025-06-26`
- `tjro-diario-2024-12-30`
- `tjro-diario-2004-07-30`

### **B. Supplements (rare)**

```
tjro-diario-YYYY-MM-DD-sufix
```

**Example:**

- `tjro-diario-2024-08-29-sup`

### **C. Generate Expected URLs**

```python
from datetime import date, timedelta

# Generate expected identifiers for a date range
start_date = date(2025, 1, 1)
end_date = date(2025, 6, 26)

current_date = start_date
while current_date <= end_date:
    identifier = f"tjro-diario-{current_date.strftime('%Y-%m-%d')}"
    url = f"https://archive.org/details/{identifier}"
    print(f"{current_date}: {url}")
    current_date += timedelta(days=1)
```

---

## **5. Bulk Access Methods**

### **A. Internet Archive Python Library**

```bash
# Install IA library
pip install internetarchive

# Download all TJRO diarios for a year
ia search 'creator:"Tribunal de Justiça de Rondônia" AND date:[2025-01-01 TO 2025-12-31]' | ia download
```

### **B. wget Bulk Download**

```bash
# Generate download list
uv run python src/ia_discovery.py --export download_list.json --year 2025

# Convert to wget URLs (custom script)
python -c "
import json
with open('download_list.json') as f:
    data = json.load(f)
for item in data['items']:
    print(f'https://archive.org/download/{item[\"identifier\"]}/{item[\"identifier\"]}.pdf')
" > urls.txt

# Bulk download
wget -i urls.txt
```

---

## **6. Monitoring and Validation**

### **A. Daily Check Script**

```bash
#!/bin/bash
# Check what was uploaded today
TODAY=$(date +%Y-%m-%d)
uv run python src/ia_discovery.py --check-identifier "tjro-diario-$TODAY"
```

### **B. Weekly Coverage Report**

```bash
#!/bin/bash
# Generate weekly coverage report
YEAR=$(date +%Y)
uv run python src/ia_discovery.py --coverage-report --year $YEAR > weekly_coverage_report.txt
```

### **C. Missing Items Detection**

```bash
# Find missing items and generate retry list
uv run python src/ia_discovery.py --coverage-report --export missing_items.json --year 2025
```

---

## **7. RSS/Atom Feeds**

Internet Archive provides feeds for new uploads:

### **A. By Creator**

```
https://archive.org/services/search/v1/scrape?q=creator:"Tribunal de Justiça de Rondônia"&count=100
```

### **B. By Collection**

```
https://archive.org/services/search/v1/scrape?q=collection:opensource AND creator:"Tribunal de Justiça de Rondônia"&count=100
```

---

## **8. Data Export Formats**

Our discovery tool supports multiple export formats:

### **A. JSON (Complete)**

```bash
uv run python src/ia_discovery.py --export inventory.json --format json
```

### **B. CSV (Tabular)**

```bash
uv run python src/ia_discovery.py --export inventory.csv --format csv
```

### **C. URLs Only (Simple)**

```bash
uv run python src/ia_discovery.py --export urls.txt --format urls_only
```

---

## **9. Integration with Existing Pipeline**

### **A. Post-Upload Validation**

```python
# After uploading, verify it's accessible
import time
from src.ia_discovery import IADiscovery

discovery = IADiscovery()

# Wait for IA processing (usually 1-5 minutes)
time.sleep(60)

# Check if upload was successful
exists = discovery.check_identifier_exists("tjro-diario-2025-06-26")
if exists:
    print("✅ Upload confirmed!")
else:
    print("❌ Upload may have failed")
```

### **B. Gap Detection and Retry**

```python
# Find missing items and add to retry queue
report = discovery.generate_coverage_report(year=2025)
missing_dates = report['missing_dates']

for date_str in missing_dates:
    # Add to retry queue or re-process
    print(f"Missing: {date_str}")
```

---

## **10. URL Patterns for Direct Access**

### **A. Item Detail Page**

```
https://archive.org/details/{identifier}
```

### **B. Direct PDF Download**

```
https://archive.org/download/{identifier}/{identifier}.pdf
```

### **C. Metadata JSON**

```
https://archive.org/metadata/{identifier}
```

### **D. Thumbnail/Preview**

```
https://archive.org/services/img/{identifier}
```

---

## **📊 Example Output**

When you run discovery commands, you'll see output like:

```
📚 Found 115 TJRO diarios in Internet Archive:
================================================================================
  1. tjro-diario-2025-06-26
     Title: Diário da Justiça TJRO - 26/06/2025
     Date: 2025-06-26
     Downloads: 5 | Size: 2,456,789 bytes
     URL: https://archive.org/details/tjro-diario-2025-06-26

  2. tjro-diario-2025-06-25
     Title: Diário da Justiça TJRO - 25/06/2025
     Date: 2025-06-25
     Downloads: 12 | Size: 3,123,456 bytes
     URL: https://archive.org/details/tjro-diario-2025-06-25
```

This comprehensive discovery system ensures you can always find, list, and access your uploaded TJRO diarios through multiple methods! 🎯
