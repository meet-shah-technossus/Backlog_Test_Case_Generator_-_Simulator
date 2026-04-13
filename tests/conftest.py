"""
pytest configuration for the integration test suite.
"""
import pytest


def pytest_configure(config):
    """Register custom markers to suppress PytestUnknownMarkWarning."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
