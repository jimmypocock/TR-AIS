"""
Track Controller - Create, modify, and control tracks.

Handles all track-related operations in Ableton Live.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AbletonClient


@dataclass
class Track:
    """Represents an Ableton track."""
    index: int
    name: str
    type: str  # "midi", "audio", "return", "master"
    armed: bool = False
    muted: bool = False
    soloed: bool = False
    volume: float = 0.85
    pan: float = 0.0
    color: int = 0
    devices: list = field(default_factory=list)


class TrackController:
    """
    Controls Ableton's tracks.

    Usage:
        # Create tracks
        idx = await client.tracks.create_midi("Drums")
        idx = await client.tracks.create_audio("Vocals")

        # Modify tracks
        await client.tracks.set_volume(0, 0.8)
        await client.tracks.set_pan(0, -0.3)
        await client.tracks.set_mute(0, True)

        # Query tracks
        count = await client.tracks.get_count()
        name = await client.tracks.get_name(0)
    """

    def __init__(self, client: "AbletonClient"):
        self._client = client

    # --- Track Creation ---

    async def create_midi(self, name: str = None, index: int = -1) -> Optional[int]:
        """
        Create a new MIDI track.

        Args:
            name: Track name (optional)
            index: Position to insert (-1 = end)

        Returns:
            Index of created track, or None on failure
        """
        self._client.send("/live/song/create_midi_track", index)
        await asyncio.sleep(0.1)

        track_count = await self.get_count()
        new_index = track_count - 1 if track_count else None

        if name and new_index is not None:
            await self.set_name(new_index, name)

        return new_index

    async def create_audio(self, name: str = None, index: int = -1) -> Optional[int]:
        """
        Create a new audio track.

        Args:
            name: Track name (optional)
            index: Position to insert (-1 = end)

        Returns:
            Index of created track, or None on failure
        """
        self._client.send("/live/song/create_audio_track", index)
        await asyncio.sleep(0.1)

        track_count = await self.get_count()
        new_index = track_count - 1 if track_count else None

        if name and new_index is not None:
            await self.set_name(new_index, name)

        return new_index

    async def create_return(self) -> Optional[int]:
        """Create a new return track."""
        self._client.send("/live/song/create_return_track")
        await asyncio.sleep(0.1)
        # Return tracks have separate indexing
        return None  # TODO: Get return track count

    async def delete(self, track_index: int):
        """Delete a track."""
        self._client.send("/live/song/delete_track", track_index)

    async def duplicate(self, track_index: int) -> Optional[int]:
        """Duplicate a track. Returns new track index."""
        self._client.send("/live/song/duplicate_track", track_index)
        await asyncio.sleep(0.1)
        return track_index + 1

    # --- Track Count ---

    async def get_count(self) -> Optional[int]:
        """Get number of tracks."""
        result = await self._client.send_and_wait("/live/song/get/num_tracks")
        if result:
            self._client.state.track_count = int(result[0])
            return self._client.state.track_count
        return None

    # --- Track Properties ---

    async def get_name(self, track_index: int) -> Optional[str]:
        """Get track name."""
        result = await self._client.send_and_wait(
            "/live/track/get/name", track_index,
            response_address="/live/track/get/name"
        )
        return str(result[1]) if result and len(result) > 1 else None

    async def set_name(self, track_index: int, name: str):
        """Set track name."""
        self._client.send("/live/track/set/name", track_index, name)

    async def get_color(self, track_index: int) -> Optional[int]:
        """Get track color."""
        result = await self._client.send_and_wait(
            "/live/track/get/color", track_index,
            response_address="/live/track/get/color"
        )
        return int(result[1]) if result and len(result) > 1 else None

    async def set_color(self, track_index: int, color: int):
        """Set track color."""
        self._client.send("/live/track/set/color", track_index, color)

    # --- Mixer Controls ---

    async def get_volume(self, track_index: int) -> Optional[float]:
        """Get track volume (0.0 to 1.0)."""
        result = await self._client.send_and_wait(
            "/live/track/get/volume", track_index,
            response_address="/live/track/get/volume"
        )
        return float(result[1]) if result and len(result) > 1 else None

    async def set_volume(self, track_index: int, volume: float):
        """Set track volume (0.0 to 1.0)."""
        volume = max(0.0, min(1.0, float(volume)))
        self._client.send("/live/track/set/volume", track_index, volume)

    async def get_pan(self, track_index: int) -> Optional[float]:
        """Get track pan (-1.0 to 1.0)."""
        result = await self._client.send_and_wait(
            "/live/track/get/panning", track_index,
            response_address="/live/track/get/panning"
        )
        return float(result[1]) if result and len(result) > 1 else None

    async def set_pan(self, track_index: int, pan: float):
        """Set track pan (-1.0 left, 0.0 center, 1.0 right)."""
        pan = max(-1.0, min(1.0, float(pan)))
        self._client.send("/live/track/set/panning", track_index, pan)

    # --- Mute / Solo / Arm ---

    async def get_mute(self, track_index: int) -> Optional[bool]:
        """Get track mute state."""
        result = await self._client.send_and_wait(
            "/live/track/get/mute", track_index,
            response_address="/live/track/get/mute"
        )
        return bool(result[1]) if result and len(result) > 1 else None

    async def set_mute(self, track_index: int, muted: bool):
        """Set track mute state."""
        self._client.send("/live/track/set/mute", track_index, int(muted))

    async def get_solo(self, track_index: int) -> Optional[bool]:
        """Get track solo state."""
        result = await self._client.send_and_wait(
            "/live/track/get/solo", track_index,
            response_address="/live/track/get/solo"
        )
        return bool(result[1]) if result and len(result) > 1 else None

    async def set_solo(self, track_index: int, soloed: bool):
        """Set track solo state."""
        self._client.send("/live/track/set/solo", track_index, int(soloed))

    async def get_arm(self, track_index: int) -> Optional[bool]:
        """Get track arm state."""
        result = await self._client.send_and_wait(
            "/live/track/get/arm", track_index,
            response_address="/live/track/get/arm"
        )
        return bool(result[1]) if result and len(result) > 1 else None

    async def set_arm(self, track_index: int, armed: bool):
        """Set track arm state (for recording)."""
        self._client.send("/live/track/set/arm", track_index, int(armed))

    # --- Sends ---

    async def get_send(self, track_index: int, send_index: int) -> Optional[float]:
        """Get send level (0.0 to 1.0)."""
        result = await self._client.send_and_wait(
            "/live/track/get/send", track_index, send_index,
            response_address="/live/track/get/send"
        )
        return float(result[2]) if result and len(result) > 2 else None

    async def set_send(self, track_index: int, send_index: int, level: float):
        """Set send level (0.0 to 1.0)."""
        level = max(0.0, min(1.0, float(level)))
        self._client.send("/live/track/set/send", track_index, send_index, level)

    # --- Clips ---

    async def stop_all_clips(self, track_index: int):
        """Stop all clips on a track."""
        self._client.send("/live/track/stop_all_clips", track_index)
