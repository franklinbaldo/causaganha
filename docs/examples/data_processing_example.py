# Example: Processing Judicial Data

# This is a conceptual example.
# Assume 'judicial_decisions.json' is in a known accessible path or
# that we have a function to load it.

import json

def load_mock_data(file_path):
    """Loads mock data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} is not a valid JSON.")
        return []

def filter_decisions_by_court(decisions, court_name):
    """Filters decisions by a specific court."""
    return [d for d in decisions if d.get("court") == court_name]

def count_keywords(decisions):
    """Counts the occurrences of keywords across all decisions."""
    keyword_counts = {}
    for decision in decisions:
        for keyword in decision.get("keywords", []):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
    return keyword_counts

def main():
    # Adjust the path if your mock data is located elsewhere relative to this script
    # For this example, we assume it's in a directory that Python can access.
    # If tests/mock_data/ is not in sys.path, this direct relative path might not work
    # depending on where you run the script from.
    # A more robust solution in a real application would use absolute paths
    # or ensure the data path is correctly resolved.

    # Path for when running from repository root:
    mock_data_path = "tests/mock_data/judicial_decisions.json"

    # If you were running this example script from within docs/examples/:
    # mock_data_path = "../../tests/mock_data/judicial_decisions.json"

    decisions_data = load_mock_data(mock_data_path)

    if not decisions_data:
        print("No data loaded. Exiting example.")
        return

    print(f"Loaded {len(decisions_data)} decisions.\n")

    supreme_court_cases = filter_decisions_by_court(decisions_data, "Supreme Court")
    print(f"Found {len(supreme_court_cases)} Supreme Court cases:")
    for case in supreme_court_cases:
        print(f"  - Case ID: {case.get('case_id')}, Outcome: {case.get('outcome')}")
    print("\n")

    district_court_cases = filter_decisions_by_court(decisions_data, "District Court")
    print(f"Found {len(district_court_cases)} District Court cases:")
    for case in district_court_cases:
        print(f"  - Case ID: {case.get('case_id')}, Outcome: {case.get('outcome')}")
    print("\n")

    all_keywords = count_keywords(decisions_data)
    print("Keyword counts across all loaded decisions:")
    for keyword, count in all_keywords.items():
        print(f"  - \"{keyword}\": {count}")

if __name__ == "__main__":
    main()
