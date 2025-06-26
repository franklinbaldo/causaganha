"""Simple configuration management for CausaGanha."""

import toml
from pathlib import Path
from typing import Dict, Any

DEFAULT_CONFIG = {
    "database": {"path": "data/causaganha.duckdb"},
    "trueskill": {"mu": 25.0, "sigma": 8.333, "beta": 4.167},
    "logging": {"level": "INFO"},
}


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load configuration from file or return defaults."""
    if config_path is None:
        config_path = Path("config.toml")

    if config_path.exists():
        config = toml.load(config_path)
        # Merge with defaults
        result = DEFAULT_CONFIG.copy()
        for key, value in config.items():
            if isinstance(value, dict) and key in result:
                result[key].update(value)
            else:
                result[key] = value
        return result
    return DEFAULT_CONFIG.copy()
