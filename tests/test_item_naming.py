import pytest
from datetime import date
from scripts.pipeline.ia_s3 import get_ia_item_id as get_ia_item_id_s3
from djen_backup.archive import get_ia_item_id as get_ia_item_id_archive

def test_get_ia_item_id():
    assert get_ia_item_id_s3("TJRO", "2025-03-19") == "djen-tjro-2025"
    assert get_ia_item_id_s3("TRE-AC", "2024-07-01") == "djen-tre-ac-2024"
    assert get_ia_item_id_s3("stf", "2023-01-01") == "djen-stf-2023"

    assert get_ia_item_id_archive("TJRO", date(2025, 3, 19)) == "djen-tjro-2025"
    assert get_ia_item_id_archive("TRE-AC", date(2024, 7, 1)) == "djen-tre-ac-2024"
    assert get_ia_item_id_archive("stf", date(2023, 1, 1)) == "djen-stf-2023"
