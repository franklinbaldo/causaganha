import re

with open("tests/dashboard/test_generate_data.py", "r") as f:
    content = f.read()

# Fix ARG005 by removing unused args
content = content.replace("lambda *args: None", "lambda *_: None")

# Fix ANN001 by adding type hints
content = content.replace("def test_fetch_kilo_ready_count_all_success(mock_urlopen) -> None:", "def test_fetch_kilo_ready_count_all_success(mock_urlopen: MagicMock) -> None:")
content = content.replace("def test_fetch_kilo_ready_count_with_failures(mock_urlopen) -> None:", "def test_fetch_kilo_ready_count_with_failures(mock_urlopen: MagicMock) -> None:")
content = content.replace("def test_fetch_kilo_ready_count_pending_checks(mock_urlopen) -> None:", "def test_fetch_kilo_ready_count_pending_checks(mock_urlopen: MagicMock) -> None:")
content = content.replace("def test_fetch_kilo_ready_count_empty_checks(mock_urlopen) -> None:", "def test_fetch_kilo_ready_count_empty_checks(mock_urlopen: MagicMock) -> None:")
content = content.replace("def test_fetch_kilo_ready_count_kilo_success(mock_urlopen) -> None:", "def test_fetch_kilo_ready_count_kilo_success(mock_urlopen: MagicMock) -> None:")

with open("tests/dashboard/test_generate_data.py", "w") as f:
    f.write(content)

with open("scripts/dashboard/generate-data.py", "r") as f:
    content2 = f.read()

content2 = content2.replace('date(2026, 2, 3)  # Based on target range end 2026-02-03', 'from datetime import date\n    date(2026, 2, 3)  # Based on target range end 2026-02-03')
content2 = content2.replace('from datetime import date', '')

with open("scripts/dashboard/generate-data.py", "w") as f:
    f.write(content2)
