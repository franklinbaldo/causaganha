def calculate_consecutive_failures(runs):
    """
    Calculates the streak of consecutive failures from a list of run dictionaries.
    Assumes runs have 'conclusion' and 'createdAt' keys.
    Returns (consecutive_failures, severity, last_failing_url).
    """
    sorted_runs = sorted(runs, key=lambda r: r.get("createdAt", ""), reverse=True)
    consecutive_failures = 0
    last_failing_url = None

    for r in sorted_runs:
        if r.get("conclusion") in ("failure", "timed_out"):
            consecutive_failures += 1
            if last_failing_url is None:
                last_failing_url = r.get("url") or r.get("html_url")
        elif r.get("conclusion") == "success":
            break

    severity = None
    if consecutive_failures >= 5:
        severity = "critical"
    elif consecutive_failures >= 3:
        severity = "warning"

    return consecutive_failures, severity, last_failing_url
