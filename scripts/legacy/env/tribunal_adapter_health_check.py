import logging
from datetime import date, timedelta

# Assuming src is in PYTHONPATH. Adjust if necessary for your project structure.
try:
    from src.tribunais import list_supported_tribunals, get_discovery
    from src.models.interfaces import DiarioDiscovery
    from src.utils.logging_config import setup_logging, get_logger
except ImportError as e:
    print(f"Error importing CausaGanha modules: {e}. Make sure PYTHONPATH is set correctly or run from project root.")
    exit(1)

# Use the project's logging setup
setup_logging(fmt="rich", level="INFO") # Use rich for console readability
logger = get_logger(__name__)

def check_adapter_health(tribunal_code: str) -> bool:
    """
    Performs health checks on a specific tribunal adapter.
    """
    logger.info(f"--- Health Check for Adapter: {tribunal_code.upper()} ---")
    overall_success = True

    try:
        discovery_impl: DiarioDiscovery = get_discovery(tribunal_code)
        logger.info(f"[{tribunal_code.upper()}] Successfully retrieved DiarioDiscovery implementation.")
    except ValueError as e:
        logger.error(f"[{tribunal_code.upper()}] FAILED to get DiarioDiscovery implementation: {e}")
        return False
    except Exception as e:
        logger.error(f"[{tribunal_code.upper()}] UNEXPECTED ERROR getting DiarioDiscovery: {e}")
        return False

    # Test get_latest_diario_url()
    try:
        logger.info(f"[{tribunal_code.upper()}] Testing get_latest_diario_url()...")
        latest_url = discovery_impl.get_latest_diario_url()
        if latest_url and latest_url.startswith("http"):
            logger.info(f"[{tribunal_code.upper()}] SUCCESS: get_latest_diario_url() returned: {latest_url}")
        elif latest_url is None:
            logger.warning(f"[{tribunal_code.upper()}] WARNING: get_latest_diario_url() returned None. This might be expected if no recent diarios or if not implemented.")
            # Not necessarily a failure, depends on tribunal and implementation.
        else:
            logger.error(f"[{tribunal_code.upper()}] FAILED: get_latest_diario_url() returned an invalid URL: {latest_url}")
            overall_success = False
    except NotImplementedError:
        logger.warning(f"[{tribunal_code.upper()}] WARNING: get_latest_diario_url() is not implemented.")
    except Exception as e:
        logger.error(f"[{tribunal_code.upper()}] FAILED: get_latest_diario_url() raised an exception: {e}", exc_info=True)
        overall_success = False

    # Test get_diario_url() for a recent date (e.g., yesterday)
    test_date = date.today() - timedelta(days=1)
    try:
        logger.info(f"[{tribunal_code.upper()}] Testing get_diario_url() for date: {test_date.isoformat()}...")
        specific_date_url = discovery_impl.get_diario_url(test_date)
        if specific_date_url and specific_date_url.startswith("http"):
            logger.info(f"[{tribunal_code.upper()}] SUCCESS: get_diario_url({test_date.isoformat()}) returned: {specific_date_url}")
        elif specific_date_url is None:
            logger.info(f"[{tribunal_code.upper()}] INFO: get_diario_url({test_date.isoformat()}) returned None. (This could be normal if no diario on this date).")
        else:
            logger.error(f"[{tribunal_code.upper()}] FAILED: get_diario_url({test_date.isoformat()}) returned an invalid URL: {specific_date_url}")
            overall_success = False
    except NotImplementedError:
        logger.warning(f"[{tribunal_code.upper()}] WARNING: get_diario_url() is not implemented.")
    except Exception as e:
        logger.error(f"[{tribunal_code.upper()}] FAILED: get_diario_url({test_date.isoformat()}) raised an exception: {e}", exc_info=True)
        overall_success = False

    logger.info(f"--- Health Check for {tribunal_code.upper()} COMPLETED. Overall Success: {overall_success} ---")
    return overall_success

def main():
    logger.info("=== Starting Tribunal Adapter Health Check ===")

    try:
        supported_tribunals = list_supported_tribunals()
    except Exception as e:
        logger.error(f"Failed to list supported tribunals: {e}. Ensure 'src.tribunais.__init__.py' is correctly configured.")
        return

    if not supported_tribunals:
        logger.warning("No supported tribunals found. Check the tribunal registry in 'src/tribunais/__init__.py'.")
        return

    logger.info(f"Found supported tribunals: {', '.join(supported_tribunals)}")

    all_adapters_healthy = True
    for tribunal in supported_tribunals:
        if not check_adapter_health(tribunal):
            all_adapters_healthy = False
        logger.info("-" * 50) # Separator

    if all_adapters_healthy:
        logger.info("✅✅✅ All checked tribunal adapters appear to be healthy (basic discovery checks passed).")
    else:
        logger.error("❌❌❌ Some tribunal adapters failed health checks. See logs above for details.")

    logger.info("=== Tribunal Adapter Health Check Finished ===")

if __name__ == "__main__":
    # This allows running the script directly.
    # For proper execution, ensure CausaGanha's src directory is in PYTHONPATH.
    # Example: PYTHONPATH=$PYTHONPATH:$(pwd) python scripts/env/tribunal_adapter_health_check.py
    main()
