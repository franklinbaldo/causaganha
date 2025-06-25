import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Current Working Directory: {os.getcwd()}")
print("sys.path:")
for p in sys.path:
    print(f"  - {p}")

try:
    import pandas
    print(f"Successfully imported pandas. Version: {pandas.__version__}")
except ImportError as e:
    print(f"Failed to import pandas: {e}")

try:
    import requests
    print(f"Successfully imported requests. Version: {requests.__version__}")
except ImportError as e:
    print(f"Failed to import requests: {e}")

try:
    import trueskill
    print(f"Successfully imported trueskill. Version: {trueskill.__version__}")
except ImportError as e:
    print(f"Failed to import trueskill: {e}")

try:
    import toml
    print(f"Successfully imported toml. Version: {toml.__version__}")
except ImportError as e:
    print(f"Failed to import toml: {e}")
