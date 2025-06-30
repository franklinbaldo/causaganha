import json
import argparse
import logging
from pathlib import Path
from collections import Counter

# Configure basic logging for the monitor script itself
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_run_results(results_path: Path) -> None:
    """
    Parses a dbt run_results.json file and logs a summary of the run.
    """
    if not results_path.exists():
        logger.error(f"dbt run_results.json not found at: {results_path}")
        return

    try:
        with open(results_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from {results_path}. File might be corrupted or not valid JSON.")
        return
    except Exception as e:
        logger.error(f"An error occurred while reading {results_path}: {e}")
        return

    logger.info(f"--- Monitoring dbt Run Results from: {results_path} ---")
    logger.info(f"Generated at: {data.get('metadata', {}).get('generated_at')}")
    logger.info(f"dbt Version: {data.get('metadata', {}).get('dbt_version')}")
    logger.info(f"Invocation ID: {data.get('metadata', {}).get('invocation_id')}")
    logger.info(f"Elapsed time for run: {data.get('elapsed_time', 0):.2f} seconds")

    results = data.get('results', [])
    if not results:
        logger.warning("No results found in the run_results.json file.")
        return

    model_statuses = Counter()
    test_statuses = Counter()
    error_messages = []
    slowest_nodes = []

    for result in results:
        node_type = result.get('unique_id', '').split('.')[0] # e.g., model, test, seed, snapshot
        status = result.get('status', 'unknown')
        execution_time = result.get('execution_time', 0)
        node_name = result.get('unique_id', 'unknown.node')

        if execution_time > 0: # Track execution time for non-trivial nodes
             slowest_nodes.append({'name': node_name, 'time': execution_time, 'status': status})

        if node_type == 'model' or node_type == 'snapshot' or node_type == 'seed':
            model_statuses[status] += 1
            if status == 'error' or status == 'fail': # dbt uses 'error' for models
                message = result.get('message', 'No error message provided.')
                error_messages.append(f"ERROR in {node_name}: {message}")
        elif node_type == 'test':
            # dbt test statuses: pass, fail, warn, error (for compilation/runtime errors)
            test_statuses[status] += 1
            if status == 'fail' or status == 'error':
                message = result.get('message', 'No failure/error message provided.')
                # For test failures, unique_id is like test.my_project.not_null_my_model_id.hash
                # We might want to extract the model it applies to if possible, or just log the test name.
                error_messages.append(f"{status.upper()} in TEST {node_name}: {message}")

    logger.info("\n--- Model/Seed/Snapshot Summary ---")
    if model_statuses:
        for status, count in model_statuses.items():
            logger.info(f"  {status.capitalize()}: {count}")
    else:
        logger.info("  No models, seeds, or snapshots were run/processed.")

    logger.info("\n--- Test Summary ---")
    if test_statuses:
        for status, count in test_statuses.items():
            logger.info(f"  {status.capitalize()}: {count}")
    else:
        logger.info("  No tests were run.")

    if error_messages:
        logger.error("\n--- Errors and Failures ---")
        for msg in error_messages:
            logger.error(f"  - {msg}")
    else:
        logger.info("\n--- No errors or failures reported in this run. ---")

    # Log slowest nodes
    if slowest_nodes:
        slowest_nodes.sort(key=lambda x: x['time'], reverse=True)
        logger.info("\n--- Top 5 Slowest Nodes ---")
        for i, node_info in enumerate(slowest_nodes[:5]):
            logger.info(f"  {i+1}. {node_info['name']}: {node_info['time']:.2f}s (Status: {node_info['status']})")

    logger.info("\n--- End of dbt Run Monitoring ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a dbt run by parsing run_results.json.")
    parser.add_argument(
        "run_results_path",
        type=Path,
        help="Path to the dbt run_results.json file (usually target/run_results.json)",
        default=Path("dbt/target/run_results.json"), # Default path assuming dbt project is in 'dbt/'
        nargs='?' # Makes the argument optional, using default if not provided
    )
    parser.add_argument(
        "--dbt-project-dir",
        type=Path,
        help="Path to the dbt project directory. If provided, run_results_path will be relative to this.",
        default=Path("dbt") # Default dbt project directory
    )


    args = parser.parse_args()

    # Determine the correct path for run_results.json
    # If run_results_path is absolute, use it. Otherwise, consider it relative to dbt_project_dir/target/
    # The default nargs='?' for run_results_path means it might not be explicitly provided,
    # so we construct it based on dbt_project_dir.

    effective_run_results_path: Path
    if args.run_results_path.is_absolute():
        effective_run_results_path = args.run_results_path
    elif args.run_results_path.name == 'run_results.json' and args.run_results_path.parent.name == 'target': # default was used
         effective_run_results_path = args.dbt_project_dir / "target" / "run_results.json"
    else: # User provided a relative path for run_results_path
        effective_run_results_path = args.run_results_path


    logger.info(f"Attempting to monitor dbt run from: {effective_run_results_path.resolve()}")
    parse_run_results(effective_run_results_path)

    # Example usage:
    # python scripts/db/monitor_dbt_run.py
    # python scripts/db/monitor_dbt_run.py path/to/your/dbt_project/target/run_results.json
    # python scripts/db/monitor_dbt_run.py --dbt-project-dir path/to/your/dbt_project
```

This script provides basic monitoring by parsing the `run_results.json` file.
The diff for this new file would be the entire file content. I'll create the diff file `001_miguel-torres_code.diff` (or rather, append to it, since it already exists for the previous change).

Since I can't append to a diff file with the current tools, I will create a new diff file for this script: `002_miguel-torres_code.diff`.

The content of `src-dev/002_miguel-torres_code.diff` will be:
```diff
--- /dev/null
+++ b/scripts/db/monitor_dbt_run.py
@@ -0,0 +1,123 @@
+import json
+import argparse
+import logging
+from pathlib import Path
+from collections import Counter
+
+# Configure basic logging for the monitor script itself
+logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
+logger = logging.getLogger(__name__)
+
+def parse_run_results(results_path: Path) -> None:
+    """
+    Parses a dbt run_results.json file and logs a summary of the run.
+    """
+    if not results_path.exists():
+        logger.error(f"dbt run_results.json not found at: {results_path}")
+        return
+
+    try:
+        with open(results_path, 'r') as f:
+            data = json.load(f)
+    except json.JSONDecodeError:
+        logger.error(f"Failed to parse JSON from {results_path}. File might be corrupted or not valid JSON.")
+        return
+    except Exception as e:
+        logger.error(f"An error occurred while reading {results_path}: {e}")
+        return
+
+    logger.info(f"--- Monitoring dbt Run Results from: {results_path} ---")
+    logger.info(f"Generated at: {data.get('metadata', {}).get('generated_at')}")
+    logger.info(f"dbt Version: {data.get('metadata', {}).get('dbt_version')}")
+    logger.info(f"Invocation ID: {data.get('metadata', {}).get('invocation_id')}")
+    logger.info(f"Elapsed time for run: {data.get('elapsed_time', 0):.2f} seconds")
+
+    results = data.get('results', [])
+    if not results:
+        logger.warning("No results found in the run_results.json file.")
+        return
+
+    model_statuses = Counter()
+    test_statuses = Counter()
+    error_messages = []
+    slowest_nodes = []
+
+    for result in results:
+        node_type = result.get('unique_id', '').split('.')[0] # e.g., model, test, seed, snapshot
+        status = result.get('status', 'unknown')
+        execution_time = result.get('execution_time', 0)
+        node_name = result.get('unique_id', 'unknown.node')
+
+        if execution_time > 0: # Track execution time for non-trivial nodes
+             slowest_nodes.append({'name': node_name, 'time': execution_time, 'status': status})
+
+        if node_type == 'model' or node_type == 'snapshot' or node_type == 'seed':
+            model_statuses[status] += 1
+            if status == 'error' or status == 'fail': # dbt uses 'error' for models
+                message = result.get('message', 'No error message provided.')
+                error_messages.append(f"ERROR in {node_name}: {message}")
+        elif node_type == 'test':
+            # dbt test statuses: pass, fail, warn, error (for compilation/runtime errors)
+            test_statuses[status] += 1
+            if status == 'fail' or status == 'error':
+                message = result.get('message', 'No failure/error message provided.')
+                # For test failures, unique_id is like test.my_project.not_null_my_model_id.hash
+                # We might want to extract the model it applies to if possible, or just log the test name.
+                error_messages.append(f"{status.upper()} in TEST {node_name}: {message}")
+
+    logger.info("\n--- Model/Seed/Snapshot Summary ---")
+    if model_statuses:
+        for status, count in model_statuses.items():
+            logger.info(f"  {status.capitalize()}: {count}")
+    else:
+        logger.info("  No models, seeds, or snapshots were run/processed.")
+
+    logger.info("\n--- Test Summary ---")
+    if test_statuses:
+        for status, count in test_statuses.items():
+            logger.info(f"  {status.capitalize()}: {count}")
+    else:
+        logger.info("  No tests were run.")
+
+    if error_messages:
+        logger.error("\n--- Errors and Failures ---")
+        for msg in error_messages:
+            logger.error(f"  - {msg}")
+    else:
+        logger.info("\n--- No errors or failures reported in this run. ---")
+
+    # Log slowest nodes
+    if slowest_nodes:
+        slowest_nodes.sort(key=lambda x: x['time'], reverse=True)
+        logger.info("\n--- Top 5 Slowest Nodes ---")
+        for i, node_info in enumerate(slowest_nodes[:5]):
+            logger.info(f"  {i+1}. {node_info['name']}: {node_info['time']:.2f}s (Status: {node_info['status']})")
+
+    logger.info("\n--- End of dbt Run Monitoring ---")
+
+
+if __name__ == "__main__":
+    parser = argparse.ArgumentParser(description="Monitor a dbt run by parsing run_results.json.")
+    parser.add_argument(
+        "run_results_path",
+        type=Path,
+        help="Path to the dbt run_results.json file (usually target/run_results.json)",
+        default=Path("dbt/target/run_results.json"), # Default path assuming dbt project is in 'dbt/'
+        nargs='?' # Makes the argument optional, using default if not provided
+    )
+    parser.add_argument(
+        "--dbt-project-dir",
+        type=Path,
+        help="Path to the dbt project directory. If provided, run_results_path will be relative to this.",
+        default=Path("dbt") # Default dbt project directory
+    )
+
+    args = parser.parse_args()
+
+    effective_run_results_path: Path
+    if args.run_results_path.is_absolute():
+        effective_run_results_path = args.run_results_path
+    elif args.run_results_path.name == 'run_results.json' and args.run_results_path.parent.name == 'target': # default was used
+         effective_run_results_path = args.dbt_project_dir / "target" / "run_results.json"
+    else: # User provided a relative path for run_results_path
+        effective_run_results_path = args.run_results_path
+
+    logger.info(f"Attempting to monitor dbt run from: {effective_run_results_path.resolve()}")
+    parse_run_results(effective_run_results_path)
+
+    # Example usage:
+    # python scripts/db/monitor_dbt_run.py
+    # python scripts/db/monitor_dbt_run.py path/to/your/dbt_project/target/run_results.json
+    # python scripts/db/monitor_dbt_run.py --dbt-project-dir path/to/your/dbt_project

```
