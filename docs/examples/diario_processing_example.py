"""Example: Running the pipeline for multiple tribunals.

See the *Multi-tribunal* section in ``docs/faq.md`` for details.
"""

import subprocess


def process_diario(date: str, tribunal: str = "TJRO") -> None:
    """Execute the CLI to process a single diário."""
    subprocess.run(
        [
            "causaganha",
            "pipeline",
            "run",
            "--tribunal",
            tribunal,
            "--date",
            date,
        ],
        check=False,
    )


if __name__ == "__main__":
    print("Processando diário do TJRO...")
    process_diario("2025-06-24")
    print("Processando diário do TJSP...")
    process_diario("2025-06-24", tribunal="TJSP")
