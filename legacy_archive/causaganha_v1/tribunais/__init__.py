"""Tribunal registry and factory functions.

This module provides a unified interface for accessing tribunal-specific
implementations through the new Diario dataclass system.
"""

from typing import Dict, List, Type

from causaganha_v1.models.interfaces import (
    DiarioAnalyzer,
    DiarioDiscovery,
    DiarioDownloader,
    TribunalAdapter,
)

from .tjro.adapter import TJROAdapter
from .tjro.analyze_adapter import TJROAnalyzer

# Import tribunal-specific implementations
from .tjro.discovery import TJRODiscovery
from .tjro.download_adapter import TJRODownloader


# Registry for tribunal-specific implementations
_DISCOVERIES: dict[str, type[DiarioDiscovery]] = {
    "tjro": TJRODiscovery,
}

_DOWNLOADERS: dict[str, type[DiarioDownloader]] = {
    "tjro": TJRODownloader,
}

_ANALYZERS: dict[str, type[DiarioAnalyzer]] = {
    "tjro": TJROAnalyzer,
}

_ADAPTERS: dict[str, type[TribunalAdapter]] = {
    "tjro": TJROAdapter,
}


def get_discovery(tribunal: str) -> DiarioDiscovery:
    """Get discovery implementation for tribunal.

    Args:
        tribunal: Tribunal code (e.g., 'tjro', 'tjsp')

    Returns:
        DiarioDiscovery implementation

    Raises:
        ValueError: If tribunal is not supported
    """
    if tribunal not in _DISCOVERIES:
        supported = list_supported_tribunals()
        raise ValueError(f"Unsupported tribunal: {tribunal}. Supported: {supported}")
    return _DISCOVERIES[tribunal]()


def get_downloader(tribunal: str) -> DiarioDownloader:
    """Get downloader implementation for tribunal.

    Args:
        tribunal: Tribunal code (e.g., 'tjro', 'tjsp')

    Returns:
        DiarioDownloader implementation

    Raises:
        ValueError: If tribunal is not supported
    """
    if tribunal not in _DOWNLOADERS:
        supported = list_supported_tribunals()
        raise ValueError(f"Unsupported tribunal: {tribunal}. Supported: {supported}")
    return _DOWNLOADERS[tribunal]()


def get_analyzer(tribunal: str) -> DiarioAnalyzer:
    """Get analyzer implementation for tribunal.

    Args:
        tribunal: Tribunal code (e.g., 'tjro', 'tjsp')

    Returns:
        DiarioAnalyzer implementation

    Raises:
        ValueError: If tribunal is not supported
    """
    if tribunal not in _ANALYZERS:
        supported = list_supported_tribunals()
        raise ValueError(f"Unsupported tribunal: {tribunal}. Supported: {supported}")
    return _ANALYZERS[tribunal]()


def get_adapter(tribunal: str) -> TribunalAdapter:
    """Get complete tribunal adapter.

    This is the recommended way to get a tribunal implementation
    as it provides all functionality in one object.

    Args:
        tribunal: Tribunal code (e.g., 'tjro', 'tjsp')

    Returns:
        TribunalAdapter implementation

    Raises:
        ValueError: If tribunal is not supported
    """
    if tribunal not in _ADAPTERS:
        supported = list_supported_tribunals()
        raise ValueError(f"Unsupported tribunal: {tribunal}. Supported: {supported}")
    return _ADAPTERS[tribunal]()


def list_supported_tribunals() -> list[str]:
    """Get list of supported tribunals.

    Returns:
        List of tribunal codes
    """
    return list(_DISCOVERIES.keys())


def is_tribunal_supported(tribunal: str) -> bool:
    """Check if a tribunal is supported.

    Args:
        tribunal: Tribunal code to check

    Returns:
        True if supported, False otherwise
    """
    return tribunal in _DISCOVERIES


def register_tribunal(
    tribunal_code: str,
    discovery_class: type[DiarioDiscovery],
    downloader_class: type[DiarioDownloader],
    analyzer_class: type[DiarioAnalyzer],
    adapter_class: type[TribunalAdapter],
) -> None:
    """Register a new tribunal implementation.

    This allows for dynamic registration of new tribunals at runtime.

    Args:
        tribunal_code: Unique code for the tribunal
        discovery_class: DiarioDiscovery implementation
        downloader_class: DiarioDownloader implementation
        analyzer_class: DiarioAnalyzer implementation
        adapter_class: TribunalAdapter implementation
    """
    _DISCOVERIES[tribunal_code] = discovery_class
    _DOWNLOADERS[tribunal_code] = downloader_class
    _ANALYZERS[tribunal_code] = analyzer_class
    _ADAPTERS[tribunal_code] = adapter_class


# Convenience functions for backward compatibility
def get_tjro_discovery() -> TJRODiscovery:
    """Get TJRO discovery implementation directly."""
    return TJRODiscovery()


def get_tjro_downloader() -> TJRODownloader:
    """Get TJRO downloader implementation directly."""
    return TJRODownloader()


def get_tjro_analyzer() -> TJROAnalyzer:
    """Get TJRO analyzer implementation directly."""
    return TJROAnalyzer()


def get_tjro_adapter() -> TJROAdapter:
    """Get TJRO complete adapter directly."""
    return TJROAdapter()
