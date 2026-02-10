"""
Session Cache for Ableton AI Assistant.

Queries and caches the current state of the Ableton session so Claude
can understand track names, devices, and other context.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

from .ableton import AbletonClient


@dataclass
class CachedDevice:
    """Cached device information."""
    index: int
    name: str
    class_name: str = ""
    type: str = ""


@dataclass
class CachedTrack:
    """Cached track information."""
    index: int
    name: str
    type: str = "midi"  # midi, audio, return, master
    volume: float = 0.85
    pan: float = 0.0
    muted: bool = False
    soloed: bool = False
    armed: bool = False
    devices: list[CachedDevice] = field(default_factory=list)


@dataclass
class SessionState:
    """Complete cached session state."""
    tempo: float = 120.0
    playing: bool = False
    recording: bool = False
    metronome: bool = False
    tracks: list[CachedTrack] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "tempo": self.tempo,
            "playing": self.playing,
            "recording": self.recording,
            "metronome": self.metronome,
            "tracks": [
                {
                    "index": t.index,
                    "name": t.name,
                    "type": t.type,
                    "volume": round(t.volume, 2),
                    "pan": round(t.pan, 2),
                    "muted": t.muted,
                    "soloed": t.soloed,
                    "armed": t.armed,
                    "devices": [
                        {
                            "index": d.index,
                            "name": d.name,
                            "class_name": d.class_name,
                            "type": d.type,
                        }
                        for d in t.devices
                    ]
                }
                for t in self.tracks
            ]
        }


class SessionCache:
    """
    Caches the current state of the Ableton session.

    Usage:
        client = AbletonClient()
        await client.connect()

        cache = SessionCache(client)
        await cache.refresh()

        print(cache.state.tempo)
        print(cache.state.tracks[0].name)

        # Get as dict for Claude context
        state_dict = cache.state.to_dict()
    """

    def __init__(self, client: AbletonClient):
        """Initialize cache with Ableton client.

        Args:
            client: Connected AbletonClient instance
        """
        self._client = client
        self._state = SessionState()

    @property
    def state(self) -> SessionState:
        """Get current cached state."""
        return self._state

    async def refresh(self, include_devices: bool = True) -> SessionState:
        """
        Refresh the entire session state from Ableton.

        Args:
            include_devices: Whether to include device info (slower)

        Returns:
            Updated SessionState
        """
        try:
            # Transport state
            self._state.tempo = await self._client.transport.get_tempo() or 120.0
            self._state.playing = await self._client.transport.is_playing() or False
            self._state.recording = await self._client.transport.is_recording() or False
            self._state.metronome = await self._client.transport.get_metronome() or False

            # Tracks
            self._state.tracks = []
            track_count = await self._client.tracks.get_count() or 0

            for i in range(track_count):
                try:
                    print(f"  Loading track {i + 1}/{track_count}...", end="\r")
                    track = await self._get_track_info(i, include_devices)
                    if track:
                        self._state.tracks.append(track)
                except Exception as e:
                    # Skip problematic tracks but continue
                    print(f"  [Warning] Could not load track {i}: {e}")

            # Clear the progress line
            print(" " * 40, end="\r")

        except Exception as e:
            print(f"  [Warning] Session refresh error: {e}")

        return self._state

    async def refresh_track(self, track_index: int, include_devices: bool = True) -> Optional[CachedTrack]:
        """
        Refresh a single track's state.

        Args:
            track_index: Index of track to refresh
            include_devices: Whether to include device info

        Returns:
            Updated CachedTrack or None
        """
        track = await self._get_track_info(track_index, include_devices)

        if track:
            # Update in list
            for i, t in enumerate(self._state.tracks):
                if t.index == track_index:
                    self._state.tracks[i] = track
                    return track

            # Not found, append
            self._state.tracks.append(track)

        return track

    async def _get_track_info(self, track_index: int, include_devices: bool) -> Optional[CachedTrack]:
        """Get full track information."""
        name = await self._client.tracks.get_name(track_index)
        if name is None:
            return None

        track = CachedTrack(
            index=track_index,
            name=name,
            type="midi",  # TODO: detect type from Ableton
            volume=await self._client.tracks.get_volume(track_index) or 0.85,
            pan=await self._client.tracks.get_pan(track_index) or 0.0,
            muted=await self._client.tracks.get_mute(track_index) or False,
            soloed=await self._client.tracks.get_solo(track_index) or False,
            armed=await self._client.tracks.get_arm(track_index) or False,
        )

        if include_devices:
            track.devices = await self._get_track_devices(track_index)

        return track

    async def _get_track_devices(self, track_index: int) -> list[CachedDevice]:
        """Get all devices on a track."""
        devices = []
        device_count = await self._client.devices.get_count(track_index) or 0

        for i in range(device_count):
            name = await self._client.devices.get_name(track_index, i)
            if name:
                device = CachedDevice(
                    index=i,
                    name=name,
                    class_name=await self._client.devices.get_class_name(track_index, i) or "",
                    type=await self._client.devices.get_type(track_index, i) or "",
                )
                devices.append(device)

        return devices

    def find_track_by_name(self, name: str) -> Optional[CachedTrack]:
        """
        Find a track by name (case-insensitive partial match).

        Args:
            name: Track name to search for

        Returns:
            Matching CachedTrack or None
        """
        name_lower = name.lower()

        # Exact match first
        for track in self._state.tracks:
            if track.name.lower() == name_lower:
                return track

        # Partial match
        for track in self._state.tracks:
            if name_lower in track.name.lower():
                return track

        return None

    def find_device_by_name(self, device_name: str, track_name: str = None) -> Optional[tuple[CachedTrack, CachedDevice]]:
        """
        Find a device by name, optionally within a specific track.

        Args:
            device_name: Device name to search for
            track_name: Optional track name to limit search

        Returns:
            Tuple of (track, device) or None
        """
        device_lower = device_name.lower()
        tracks_to_search = self._state.tracks

        if track_name:
            track = self.find_track_by_name(track_name)
            if track:
                tracks_to_search = [track]
            else:
                return None

        for track in tracks_to_search:
            for device in track.devices:
                if device_lower in device.name.lower() or device_lower in device.class_name.lower():
                    return (track, device)

        return None
