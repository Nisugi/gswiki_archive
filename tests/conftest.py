"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add project root to path for all tests
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_log_dir(tmp_path):
    """Provide a temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def sample_api_response():
    """Sample MediaWiki API response for testing."""
    return {
        "query": {
            "namespaces": {
                "-1": {"id": -1, "name": "Special"},
                "0": {"id": 0, "name": ""},
                "1": {"id": 1, "name": "Talk"},
                "10": {"id": 10, "name": "Template"},
                "14": {"id": 14, "name": "Category"},
            },
            "allpages": [
                {"pageid": 1, "title": "Main Page"},
                {"pageid": 2, "title": "Category:Weapons"},
                {"pageid": 3, "title": "Template:Infobox"},
            ],
        }
    }
