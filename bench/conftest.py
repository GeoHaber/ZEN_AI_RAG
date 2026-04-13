"""Shared pytest configuration for rag-test-bench."""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests that load heavy models (e.g. sentence-transformers)")
    config.addinivalue_line("markers", "live: live e2e tests — real crawl, real LLM, real embeddings (no mocks)")


def pytest_collection_modifyitems(config, items):
    """Auto-skip 'live' tests unless explicitly requested with -m live."""
    if config.getoption("-m") and "live" in config.getoption("-m"):
        return  # user explicitly asked for live tests
    skip_live = pytest.mark.skip(reason="Live tests require -m live (needs internet + LLM)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
