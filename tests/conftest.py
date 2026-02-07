"""
Pytest configuration and fixtures.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


@pytest.fixture
def ableton_config():
    """Provide test Ableton configuration."""
    from backend.ableton_engine import AbletonConfig
    return AbletonConfig(
        host="127.0.0.1",
        send_port=11000,
        receive_port=11001,
        timeout=2.0
    )


@pytest.fixture
def sample_track_data():
    """Provide sample track data for testing."""
    return {
        "index": 0,
        "name": "Drums",
        "type": "midi",
        "armed": False,
        "muted": False,
        "volume": 0.85,
        "devices": [
            {"index": 0, "name": "Drum Rack", "type": "instrument"}
        ]
    }


@pytest.fixture
def sample_session_state():
    """Provide sample session state for testing."""
    return {
        "tempo": 120.0,
        "playing": False,
        "tracks": [
            {"index": 0, "name": "Drums", "type": "midi"},
            {"index": 1, "name": "Bass", "type": "midi"},
            {"index": 2, "name": "Keys", "type": "midi"},
        ]
    }
