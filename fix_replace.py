import sys

content = open("scripts/dashboard/generate-data.py").read()

search = """
                perf_metrics["causaganha_upload_success_rate"] = round(
                    (success_count / len(runs)) * 100, 2
                )
                recent_failure_stats = calculate_recent_failure_rate(runs, window_size=8)
                perf_metrics["causaganha_recent_failure_rate"] = recent_failure_stats["recent_failure_rate"]
                perf_metrics["causaganha_recent_failed_count"] = recent_failure_stats["recent_failed_count"]
                perf_metrics["causaganha_recent_window_size"] = recent_failure_stats["recent_window_size"]
                perf_metrics["causaganha_latest_failed_run_url"] = recent_failure_stats["latest_failed_run_url"]
"""

replace = """
                perf_metrics["causaganha_upload_success_rate"] = round(
                    (success_count / len(runs)) * 100, 2
                )
                recent_failure_stats = calculate_recent_failure_rate(runs, window_size=8)
                perf_metrics["causaganha_recent_failure_rate"] = recent_failure_stats[
                    "recent_failure_rate"
                ]
                perf_metrics["causaganha_recent_failed_count"] = recent_failure_stats[
                    "recent_failed_count"
                ]
                perf_metrics["causaganha_recent_window_size"] = recent_failure_stats[
                    "recent_window_size"
                ]
                perf_metrics["causaganha_latest_failed_run_url"] = recent_failure_stats[
                    "latest_failed_run_url"
                ]
"""

if search in content:
    content = content.replace(search, replace)
    open("scripts/dashboard/generate-data.py", "w").write(content)
    print("Fixed line lengths in generate-data.py")
else:
    print("Search block not found")
