# Example: Demonstrating Error Handling Concepts

# These functions simulate operations that might fail.
# They are inspired by the simulated functions in tests/test_error_simulation.py
import contextlib


def attempt_network_operation(succeed=False) -> str:
    """Simulates a network operation that might fail."""
    if succeed:
        return "Data from network"
    # Simulating a common network error
    msg = "Simulated: Failed to connect to the server."
    raise ConnectionError(msg)


def access_api_service(calls_made, limit=3) -> str:
    """Simulates accessing an API service with a rate limit."""
    if calls_made >= limit:
        # Simulating hitting an API rate limit
        msg = "Simulated: API rate limit exceeded."
        raise Exception(msg)
    return f"Data from API call {calls_made + 1}"


def process_file(file_exists=True, file_is_valid=True) -> str:
    """Simulates processing a file that might be missing or corrupted."""
    if not file_exists:
        msg = "Simulated: The specified file does not exist."
        raise FileNotFoundError(msg)
    if not file_is_valid:
        msg = "Simulated: Error reading corrupted file."
        raise OSError(msg)
    return "File content"


def main() -> None:
    # --- Network Error Example ---
    try:
        # Change to True to simulate success
        attempt_network_operation(succeed=False)
    except ConnectionError:
        pass

    # --- API Limit Example ---
    api_call_count = 0
    api_call_limit = 2
    for _i in range(api_call_limit + 1):  # Try one more time than the limit
        try:
            access_api_service(api_call_count, limit=api_call_limit)
            api_call_count += 1
        except Exception:
            break  # Stop trying after hitting the limit in this example

    # --- File Processing Error Examples ---
    # Scenario 1: File does not exist
    with contextlib.suppress(FileNotFoundError):
        process_file(file_exists=False)

    # Scenario 2: File is corrupted
    with contextlib.suppress(OSError):
        process_file(file_exists=True, file_is_valid=False)

    # Scenario 3: File is processed successfully
    try:
        process_file(file_exists=True, file_is_valid=True)
    except Exception:  # Generic catch-all for unexpected issues
        pass


if __name__ == "__main__":
    main()
