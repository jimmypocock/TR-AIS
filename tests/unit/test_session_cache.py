"""
Unit tests for Session Cache.

These tests verify the session caching logic using mocked Ableton client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.session_cache import (
    SessionCache,
    SessionState,
    CachedTrack,
    CachedDevice,
)


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_values(self):
        """Test default session state."""
        state = SessionState()
        assert state.tempo == 120.0
        assert state.playing is False
        assert state.recording is False
        assert state.metronome is False
        assert state.tracks == []

    def test_to_dict(self):
        """Test converting to dictionary."""
        state = SessionState(
            tempo=100.0,
            playing=True,
            tracks=[
                CachedTrack(
                    index=0,
                    name="Drums",
                    volume=0.85,
                    devices=[
                        CachedDevice(index=0, name="Drum Rack", class_name="DrumRack")
                    ]
                )
            ]
        )
        d = state.to_dict()

        assert d["tempo"] == 100.0
        assert d["playing"] is True
        assert len(d["tracks"]) == 1
        assert d["tracks"][0]["name"] == "Drums"
        assert len(d["tracks"][0]["devices"]) == 1
        assert d["tracks"][0]["devices"][0]["name"] == "Drum Rack"


class TestCachedTrack:
    """Tests for CachedTrack dataclass."""

    def test_default_values(self):
        """Test default track values."""
        track = CachedTrack(index=0, name="Test")
        assert track.type == "midi"
        assert track.volume == 0.85
        assert track.pan == 0.0
        assert track.muted is False
        assert track.soloed is False
        assert track.armed is False
        assert track.devices == []

    def test_with_devices(self):
        """Test track with devices."""
        track = CachedTrack(
            index=0,
            name="Synth",
            devices=[
                CachedDevice(index=0, name="Wavetable", class_name="Wavetable"),
                CachedDevice(index=1, name="Reverb", class_name="Reverb"),
            ]
        )
        assert len(track.devices) == 2
        assert track.devices[0].name == "Wavetable"
        assert track.devices[1].name == "Reverb"


class TestCachedDevice:
    """Tests for CachedDevice dataclass."""

    def test_default_values(self):
        """Test default device values."""
        device = CachedDevice(index=0, name="Compressor")
        assert device.class_name == ""
        assert device.type == ""

    def test_with_values(self):
        """Test device with values."""
        device = CachedDevice(
            index=0,
            name="My Wavetable",
            class_name="Wavetable",
            type="instrument"
        )
        assert device.name == "My Wavetable"
        assert device.class_name == "Wavetable"


class TestSessionCache:
    """Tests for SessionCache."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Ableton client."""
        client = MagicMock()

        # Mock transport
        client.transport = MagicMock()
        client.transport.get_tempo = AsyncMock(return_value=120.0)
        client.transport.is_playing = AsyncMock(return_value=False)
        client.transport.is_recording = AsyncMock(return_value=False)
        client.transport.get_metronome = AsyncMock(return_value=False)

        # Mock tracks
        client.tracks = MagicMock()
        client.tracks.get_count = AsyncMock(return_value=2)
        client.tracks.get_name = AsyncMock(side_effect=["Drums", "Bass"])
        client.tracks.get_volume = AsyncMock(return_value=0.85)
        client.tracks.get_pan = AsyncMock(return_value=0.0)
        client.tracks.get_mute = AsyncMock(return_value=False)
        client.tracks.get_solo = AsyncMock(return_value=False)
        client.tracks.get_arm = AsyncMock(return_value=False)

        # Mock devices
        client.devices = MagicMock()
        client.devices.get_count = AsyncMock(return_value=1)
        client.devices.get_name = AsyncMock(return_value="Drum Rack")
        client.devices.get_class_name = AsyncMock(return_value="DrumGroupDevice")
        client.devices.get_type = AsyncMock(return_value="instrument")

        return client

    @pytest.fixture
    def cache(self, mock_client):
        """Create cache with mock client."""
        return SessionCache(mock_client)

    def test_initial_state(self, cache):
        """Test cache starts with default state."""
        assert cache.state.tempo == 120.0
        assert cache.state.tracks == []

    @pytest.mark.asyncio
    async def test_refresh_transport(self, cache, mock_client):
        """Test refreshing transport state."""
        mock_client.transport.get_tempo = AsyncMock(return_value=95.0)
        mock_client.transport.is_playing = AsyncMock(return_value=True)
        mock_client.tracks.get_count = AsyncMock(return_value=0)

        await cache.refresh()

        assert cache.state.tempo == 95.0
        assert cache.state.playing is True

    @pytest.mark.asyncio
    async def test_refresh_tracks(self, cache, mock_client):
        """Test refreshing track state."""
        await cache.refresh()

        assert len(cache.state.tracks) == 2
        assert cache.state.tracks[0].name == "Drums"
        assert cache.state.tracks[1].name == "Bass"

    @pytest.mark.asyncio
    async def test_refresh_without_devices(self, cache, mock_client):
        """Test refreshing without device info."""
        await cache.refresh(include_devices=False)

        assert len(cache.state.tracks) == 2
        # Devices should be empty
        assert cache.state.tracks[0].devices == []

    @pytest.mark.asyncio
    async def test_refresh_with_devices(self, cache, mock_client):
        """Test refreshing with device info."""
        await cache.refresh(include_devices=True)

        assert len(cache.state.tracks) == 2
        assert len(cache.state.tracks[0].devices) == 1
        assert cache.state.tracks[0].devices[0].name == "Drum Rack"


class TestSessionCacheSearch:
    """Tests for session cache search methods."""

    @pytest.fixture
    def cache_with_tracks(self):
        """Create cache with pre-populated tracks."""
        client = MagicMock()
        cache = SessionCache(client)

        cache._state = SessionState(
            tracks=[
                CachedTrack(
                    index=0,
                    name="Drums",
                    devices=[
                        CachedDevice(index=0, name="Drum Rack", class_name="DrumGroupDevice"),
                    ]
                ),
                CachedTrack(
                    index=1,
                    name="Bass Synth",
                    devices=[
                        CachedDevice(index=0, name="Wavetable", class_name="InstrumentVector"),
                        CachedDevice(index=1, name="Compressor", class_name="Compressor2"),
                    ]
                ),
                CachedTrack(
                    index=2,
                    name="Lead Synth",
                    devices=[]
                ),
            ]
        )
        return cache

    def test_find_track_exact_match(self, cache_with_tracks):
        """Test finding track by exact name."""
        track = cache_with_tracks.find_track_by_name("Drums")
        assert track is not None
        assert track.name == "Drums"
        assert track.index == 0

    def test_find_track_case_insensitive(self, cache_with_tracks):
        """Test finding track case insensitively."""
        track = cache_with_tracks.find_track_by_name("drums")
        assert track is not None
        assert track.name == "Drums"

    def test_find_track_partial_match(self, cache_with_tracks):
        """Test finding track by partial name."""
        track = cache_with_tracks.find_track_by_name("Bass")
        assert track is not None
        assert track.name == "Bass Synth"

    def test_find_track_not_found(self, cache_with_tracks):
        """Test finding non-existent track."""
        track = cache_with_tracks.find_track_by_name("Keys")
        assert track is None

    def test_find_device_by_name(self, cache_with_tracks):
        """Test finding device by name."""
        result = cache_with_tracks.find_device_by_name("Wavetable")
        assert result is not None
        track, device = result
        assert track.name == "Bass Synth"
        assert device.name == "Wavetable"

    def test_find_device_by_class_name(self, cache_with_tracks):
        """Test finding device by class name."""
        result = cache_with_tracks.find_device_by_name("Compressor2")
        assert result is not None
        track, device = result
        assert device.class_name == "Compressor2"

    def test_find_device_in_specific_track(self, cache_with_tracks):
        """Test finding device within specific track."""
        result = cache_with_tracks.find_device_by_name("Drum", track_name="Drums")
        assert result is not None
        track, device = result
        assert track.name == "Drums"
        assert device.name == "Drum Rack"

    def test_find_device_not_in_track(self, cache_with_tracks):
        """Test finding device not in specified track."""
        result = cache_with_tracks.find_device_by_name("Wavetable", track_name="Drums")
        assert result is None

    def test_find_device_not_found(self, cache_with_tracks):
        """Test finding non-existent device."""
        result = cache_with_tracks.find_device_by_name("Serum")
        assert result is None
