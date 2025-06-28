"""Example: Basic use of the database sync tool."""

import subprocess


def check_status():
    subprocess.run([
        "uv",
        "run",
        "python",
        "src/ia_database_sync.py",
        "status",
    ], check=False)


def perform_sync():
    subprocess.run([
        "uv",
        "run",
        "python",
        "src/ia_database_sync.py",
        "sync",
    ], check=False)


if __name__ == "__main__":
    print("Checking database status...")
    check_status()
    print("Synchronizing database...")
    perform_sync()
