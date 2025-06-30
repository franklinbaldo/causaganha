#!/bin/bash

set -e

TRIBUNAL_ABBREV=$1

if [ -z "$TRIBUNAL_ABBREV" ]; then
  echo "Usage: $0 <tribunal_abbrev>"
  echo "Example: $0 tjsp"
  exit 1
fi

# Convert to lowercase for directory names etc.
TRIBUNAL_LOWER=$(echo "$TRIBUNAL_ABBREV" | tr '[:upper:]' '[:lower:]')
# Convert to uppercase for class names etc.
TRIBUNAL_UPPER=$(echo "$TRIBUNAL_ABBREV" | tr '[:lower:]' '[:upper:]')
# Capitalized version for class prefixes
TRIBUNAL_CAPITALIZED="$(tr '[:lower:]' '[:upper:]' <<< ${TRIBUNAL_LOWER:0:1})${TRIBUNAL_LOWER:1}"

SRC_DIR="src/tribunais/$TRIBUNAL_LOWER"
TEST_DIR="tests/tribunais/$TRIBUNAL_LOWER"

echo "--- Bootstrapping new tribunal adapter: $TRIBUNAL_LOWER ---"

# Create source directories
mkdir -p "$SRC_DIR"
echo "Created $SRC_DIR"

# Create test directories
mkdir -p "$TEST_DIR"
echo "Created $TEST_DIR"

# --- Create __init__.py files ---
touch "$SRC_DIR/__init__.py"
touch "$TEST_DIR/__init__.py"

# --- Create discovery.py ---
cat <<EOF > "$SRC_DIR/discovery.py"
from datetime import date
from typing import Optional, List

from src.models.diario import Diario # Assuming Diario is the primary object
from src.models.interfaces import DiarioDiscovery

class ${TRIBUNAL_CAPITALIZED}Discovery(DiarioDiscovery):
    """Discovery implementation for $TRIBUNAL_UPPER."""

    def get_diario_url(self, target_date: date) -> Optional[str]:
        # TODO: Implement URL discovery logic for $TRIBUNAL_UPPER for a specific date
        # Example: return f"https://www.${TRIBUNAL_LOWER}.jus.br/diario/{target_date.strftime('%Y%m%d')}.pdf"
        print(f"Placeholder: Discovering URL for $TRIBUNAL_UPPER on {target_date}")
        return None

    def get_latest_diario_url(self) -> Optional[str]:
        # TODO: Implement logic to find the latest diario URL for $TRIBUNAL_UPPER
        print("Placeholder: Discovering latest URL for $TRIBUNAL_UPPER")
        return None

    def list_diarios_in_range(self, start_date: date, end_date: date) -> List[str]:
        # TODO: Implement logic to list all diario URLs in the date range for $TRIBUNAL_UPPER
        print(f"Placeholder: Discovering URLs for $TRIBUNAL_UPPER from {start_date} to {end_date}")
        return []

    # Helper method to create Diario objects (optional, adapt as needed)
    def discover_diarios(self, start_date: date, end_date: date) -> List[Diario]:
        diarios = []
        # Example:
        # current_date = start_date
        # while current_date <= end_date:
        #     url = self.get_diario_url(current_date)
        #     if url:
        #         diarios.append(Diario(tribunal="$TRIBUNAL_LOWER", data=current_date, url=url, filename=Path(url).name))
        #     current_date += timedelta(days=1)
        return diarios

EOF
echo "Created $SRC_DIR/discovery.py"

# --- Create downloader.py ---
cat <<EOF > "$SRC_DIR/downloader.py"
from pathlib import Path
from typing import Optional

from src.models.diario import Diario
from src.models.interfaces import DiarioDownloader

class ${TRIBUNAL_CAPITALIZED}Downloader(DiarioDownloader):
    """Downloader implementation for $TRIBUNAL_UPPER."""

    def download_diario(self, diario: Diario) -> Diario:
        # TODO: Implement PDF download logic for $TRIBUNAL_UPPER
        # Update diario.pdf_path and diario.hash if successful
        # Example:
        # target_path = Path("data/diarios_pdf") / diario.tribunal / diario.filename
        # target_path.parent.mkdir(parents=True, exist_ok=True)
        # download_url_to_file(diario.url, target_path)
        # diario.pdf_path = target_path
        # diario.hash = calculate_hash(target_path)
        # diario.status = "downloaded"
        print(f"Placeholder: Downloading {diario.url} for $TRIBUNAL_UPPER")
        diario.status = "failed_download" # Default to failed if not implemented
        return diario

    def archive_to_ia(self, diario: Diario) -> Diario:
        # TODO: Implement Internet Archive upload logic if specific to $TRIBUNAL_UPPER
        # Otherwise, a generic IA uploader might be used.
        # Update diario.ia_identifier and diario.status
        print(f"Placeholder: Archiving {diario.display_name} to IA for $TRIBUNAL_UPPER")
        diario.status = "failed_ia_upload" # Default
        return diario
EOF
echo "Created $SRC_DIR/downloader.py"

# --- Create analyzer.py ---
cat <<EOF > "$SRC_DIR/analyzer.py"
from typing import List, Dict

from src.models.diario import Diario
from src.models.interfaces import DiarioAnalyzer

class ${TRIBUNAL_CAPITALIZED}Analyzer(DiarioAnalyzer):
    """Analyzer implementation for $TRIBUNAL_UPPER."""

    def extract_decisions(self, diario: Diario) -> List[Dict]:
        # TODO: Implement decision extraction logic for $TRIBUNAL_UPPER
        # This might involve calling an LLM or other parsing logic.
        # Example:
        # if not diario.pdf_path:
        #    raise ValueError("PDF path not set in Diario object")
        # text_content = convert_pdf_to_text(diario.pdf_path)
        # decisions = parse_text_for_decisions(text_content)
        # diario.status = "analyzed"
        print(f"Placeholder: Analyzing {diario.display_name} for $TRIBUNAL_UPPER")
        return []
EOF
echo "Created $SRC_DIR/analyzer.py"

# --- Create placeholder test file ---
cat <<EOF > "$TEST_DIR/test_${TRIBUNAL_LOWER}_adapter.py"
import pytest
from datetime import date
from src.tribunais.$TRIBUNAL_LOWER.discovery import ${TRIBUNAL_CAPITALIZED}Discovery
# from src.tribunais.$TRIBUNAL_LOWER.downloader import ${TRIBUNAL_CAPITALIZED}Downloader
# from src.tribunais.$TRIBUNAL_LOWER.analyzer import ${TRIBUNAL_CAPITALIZED}Analyzer
from src.models.diario import Diario

@pytest.fixture
def ${TRIBUNAL_LOWER}_discovery():
    return ${TRIBUNAL_CAPITALIZED}Discovery()

# Add more fixtures for Downloader and Analyzer if needed

def test_${TRIBUNAL_LOWER}_discovery_placeholder(${TRIBUNAL_LOWER}_discovery):
    # TODO: Replace with actual tests for $TRIBUNAL_UPPER discovery
    # Example:
    # target_date = date(2023, 1, 1)
    # url = ${TRIBUNAL_LOWER}_discovery.get_diario_url(target_date)
    # assert url is not None
    # assert "$TRIBUNAL_LOWER" in url
    assert True, "Placeholder test for $TRIBUNAL_UPPER discovery, replace with real tests."

# TODO: Add tests for ${TRIBUNAL_CAPITALIZED}Downloader
# TODO: Add tests for ${TRIBUNAL_CAPITALIZED}Analyzer

EOF
echo "Created $TEST_DIR/test_${TRIBUNAL_LOWER}_adapter.py"

echo "\n--- Manual next steps: ---"
echo "1. Implement the TODO sections in the generated files."
echo "2. Register the new adapter classes in src/tribunais/__init__.py:"
echo "   Example:"
echo "   from .${TRIBUNAL_LOWER}.discovery import ${TRIBUNAL_CAPITALIZED}Discovery"
echo "   _DISCOVERIES['$TRIBUNAL_LOWER'] = ${TRIBUNAL_CAPITALIZED}Discovery"
echo "   (and similarly for Downloader and Analyzer)"
echo "3. Add specific Dockerfile/compose configurations if this adapter has unique dependencies or setup."
echo "   (Often, the generic Docker setup might be sufficient)."
echo "4. Write comprehensive tests in $TEST_DIR."

echo "\nBootstrap complete for $TRIBUNAL_LOWER adapter."

# Dockerfile/compose configurations are usually generic.
# If specific setup is needed (e.g. system dependencies for a new PDF parser),
# that would be a manual addition to the main Dockerfile or a new one.
# This script won't try to modify the global Dockerfile or docker-compose.yml.
# It will print a message if such considerations are needed.

if [ "$TRIBUNAL_LOWER" == "special_case_tribunal_requiring_ocr_engine" ]; then
    echo "\nNOTE: This tribunal might require special dependencies (e.g., an OCR engine)."
    echo "Please review the main Dockerfile and consider if additions are needed."
fi
