"""
Unit tests for AbletonEngine.

These tests verify the engine's internal logic without requiring
an actual Ableton connection.
"""

import pytest
from backend.ableton_engine import AbletonConfig, AbletonEngine, SessionState, Track


class TestAbletonConfig:
    """Tests for AbletonConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AbletonConfig()
        assert config.host == "127.0.0.1"
        assert config.send_port == 11000
        assert config.receive_port == 11001
        assert config.timeout == 5.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AbletonConfig(
            host="192.168.1.100",
            send_port=12000,
            receive_port=12001,
            timeout=10.0
        )
        assert config.host == "192.168.1.100"
        assert config.send_port == 12000
        assert config.receive_port == 12001
        assert config.timeout == 10.0


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_state(self):
        """Test default session state."""
        state = SessionState()
        assert state.connected is False
        assert state.tempo == 120.0
        assert state.playing is False
        assert state.recording is False
        assert state.tracks == []
        assert state.scenes == []

    def test_state_with_tracks(self):
        """Test session state with tracks."""
        track = Track(index=0, name="Drums", type="midi")
        state = SessionState(tracks=[track])
        assert len(state.tracks) == 1
        assert state.tracks[0].name == "Drums"


class TestTrack:
    """Tests for Track dataclass."""

    def test_track_defaults(self):
        """Test default track values."""
        track = Track(index=0, name="Test", type="midi")
        assert track.armed is False
        assert track.muted is False
        assert track.soloed is False
        assert track.volume == 0.85
        assert track.pan == 0.0
        assert track.devices == []

    def test_track_with_devices(self):
        """Test track with devices."""
        track = Track(
            index=0,
            name="Synth",
            type="midi",
            devices=[{"name": "Wavetable", "type": "instrument"}]
        )
        assert len(track.devices) == 1
        assert track.devices[0]["name"] == "Wavetable"


class TestAbletonEngine:
    """Tests for AbletonEngine class."""

    def test_init_default_config(self):
        """Test engine initialization with default config."""
        engine = AbletonEngine()
        assert engine.config.host == "127.0.0.1"
        assert engine.state.connected is False

    def test_init_custom_config(self, ableton_config):
        """Test engine initialization with custom config."""
        engine = AbletonEngine(config=ableton_config)
        assert engine.config.timeout == 2.0

    def test_state_not_connected_by_default(self):
        """Test that engine starts disconnected."""
        engine = AbletonEngine()
        assert engine.state.connected is False
        assert engine.client is None
        assert engine.server is None
