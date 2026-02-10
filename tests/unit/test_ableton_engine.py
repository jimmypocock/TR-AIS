"""
Unit tests for Ableton integration.

These tests verify the modules' internal logic without requiring
an actual Ableton connection.
"""

import pytest
from backend.ableton import (
    AbletonClient,
    AbletonConfig,
    SessionState,
    Track,
    Device,
    DeviceParameter,
)


class TestAbletonConfig:
    """Tests for AbletonConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AbletonConfig()
        assert config.host == "127.0.0.1"
        assert config.send_port == 11000
        assert config.receive_port == 11001
        assert config.timeout == 0.5  # Fast timeout for local OSC

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
        assert state.track_count == 0

    def test_state_modification(self):
        """Test modifying session state."""
        state = SessionState()
        state.connected = True
        state.tempo = 140.0
        state.playing = True
        assert state.connected is True
        assert state.tempo == 140.0
        assert state.playing is True


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


class TestDevice:
    """Tests for Device dataclass."""

    def test_device_defaults(self):
        """Test default device values."""
        device = Device(
            track_index=0,
            device_index=0,
            name="Wavetable"
        )
        assert device.class_name == ""
        assert device.type == ""
        assert device.parameters == []

    def test_device_with_parameters(self):
        """Test device with parameters."""
        param = DeviceParameter(
            index=0,
            name="Filter Freq",
            value=0.5,
            min=0.0,
            max=1.0
        )
        device = Device(
            track_index=0,
            device_index=0,
            name="Wavetable",
            class_name="Wavetable",
            type="instrument",
            parameters=[param]
        )
        assert len(device.parameters) == 1
        assert device.parameters[0].name == "Filter Freq"


class TestDeviceParameter:
    """Tests for DeviceParameter dataclass."""

    def test_parameter_defaults(self):
        """Test default parameter values."""
        param = DeviceParameter(
            index=0,
            name="Volume",
            value=0.85,
            min=0.0,
            max=1.0
        )
        assert param.is_quantized is False

    def test_parameter_quantized(self):
        """Test quantized parameter."""
        param = DeviceParameter(
            index=0,
            name="Waveform",
            value=2.0,
            min=0.0,
            max=5.0,
            is_quantized=True
        )
        assert param.is_quantized is True


class TestAbletonClient:
    """Tests for AbletonClient class."""

    def test_init_default_config(self):
        """Test client initialization with default config."""
        client = AbletonClient()
        assert client.config.host == "127.0.0.1"
        assert client.state.connected is False

    def test_init_custom_config(self, ableton_config):
        """Test client initialization with custom config."""
        client = AbletonClient(config=ableton_config)
        assert client.config.timeout == 2.0

    def test_state_not_connected_by_default(self):
        """Test that client starts disconnected."""
        client = AbletonClient()
        assert client.state.connected is False
        assert client.is_connected is False
        assert client._osc_client is None
        assert client._osc_server is None

    def test_controllers_lazy_initialized(self):
        """Test that controllers are lazily initialized."""
        client = AbletonClient()
        # Access controllers
        transport = client.transport
        tracks = client.tracks
        devices = client.devices
        # Verify they exist
        assert transport is not None
        assert tracks is not None
        assert devices is not None
        # Verify same instance returned
        assert client.transport is transport
        assert client.tracks is tracks
        assert client.devices is devices
