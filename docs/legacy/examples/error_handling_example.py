# Example: Demonstrating Error Handling Concepts

# These functions simulate operations that might fail.
# They are inspired by the simulated functions in tests/test_error_simulation.py

def attempt_network_operation(succeed=False):
    """Simulates a network operation that might fail."""
    print("Attempting network operation...")
    if succeed:
        print("Network operation successful.")
        return "Data from network"
    else:
        # Simulating a common network error
        raise ConnectionError("Simulated: Failed to connect to the server.")

def access_api_service(calls_made, limit=3):
    """Simulates accessing an API service with a rate limit."""
    print(f"Accessing API service (call {calls_made + 1})...")
    if calls_made >= limit:
        # Simulating hitting an API rate limit
        raise Exception("Simulated: API rate limit exceeded.")
    else:
        print("API call successful.")
        return f"Data from API call {calls_made + 1}"

def process_file(file_exists=True, file_is_valid=True):
    """Simulates processing a file that might be missing or corrupted."""
    print("Attempting to process file...")
    if not file_exists:
        raise FileNotFoundError("Simulated: The specified file does not exist.")
    if not file_is_valid:
        raise IOError("Simulated: Error reading corrupted file.")
    print("File processed successfully.")
    return "File content"

def main():
    # --- Network Error Example ---
    print("--- Example 1: Network Operation ---")
    try:
        # Change to True to simulate success
        result = attempt_network_operation(succeed=False)
        print(f"Result: {result}")
    except ConnectionError as e:
        print(f"Caught a network error: {e}")
        print("Recovery: Could retry, log error, or notify user.\n")

    # --- API Limit Example ---
    print("--- Example 2: API Limit Handling ---")
    api_call_count = 0
    api_call_limit = 2
    for i in range(api_call_limit + 1): # Try one more time than the limit
        try:
            result = access_api_service(api_call_count, limit=api_call_limit)
            print(f"Result: {result}")
            api_call_count += 1
        except Exception as e:
            print(f"Caught an API error: {e}")
            print("Recovery: Could implement backoff, wait, or notify user.\n")
            break # Stop trying after hitting the limit in this example
        print("-" * 20)

    # --- File Processing Error Examples ---
    print("--- Example 3: File Processing ---")
    # Scenario 1: File does not exist
    try:
        result = process_file(file_exists=False)
        print(f"Result: {result}")
    except FileNotFoundError as e:
        print(f"Caught a file error: {e}")
        print("Recovery: Prompt user for correct path, or skip file.\n")

    # Scenario 2: File is corrupted
    try:
        result = process_file(file_exists=True, file_is_valid=False)
        print(f"Result: {result}")
    except IOError as e:
        print(f"Caught a file error: {e}")
        print("Recovery: Quarantine file, log error, attempt repair if possible.\n")

    # Scenario 3: File is processed successfully
    try:
        result = process_file(file_exists=True, file_is_valid=True)
        print(f"Result: {result}\n")
    except Exception as e: # Generic catch-all for unexpected issues
        print(f"An unexpected error occurred: {e}\n")


if __name__ == "__main__":
    main()
