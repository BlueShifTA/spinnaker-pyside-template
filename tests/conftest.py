"""Pytest configuration and fixtures."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options."""
    parser.addoption(
        "--run-hardware",
        action="store_true",
        default=False,
        help="Run tests that require real camera hardware",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "hardware: mark test as requiring real camera hardware",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip hardware tests unless --run-hardware is passed."""
    if config.getoption("--run-hardware"):
        # --run-hardware given, don't skip hardware tests
        return

    skip_hardware = pytest.mark.skip(reason="need --run-hardware option to run")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hardware)
