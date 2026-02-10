"""
Transport Controller - Play, stop, tempo, and playback controls.

Handles all transport-related operations in Ableton Live.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AbletonClient


class TransportController:
    """
    Controls Ableton's transport functions.

    Usage:
        await client.transport.play()
        await client.transport.stop()
        await client.transport.set_tempo(120)
        tempo = await client.transport.get_tempo()
    """

    def __init__(self, client: "AbletonClient"):
        self._client = client

    # --- Playback ---

    async def play(self):
        """Start playback."""
        self._client.send("/live/song/start_playing")
        self._client.state.playing = True

    async def stop(self):
        """Stop playback."""
        self._client.send("/live/song/stop_playing")
        self._client.state.playing = False

    async def continue_playing(self):
        """Continue playback from current position."""
        self._client.send("/live/song/continue_playing")
        self._client.state.playing = True

    async def stop_all_clips(self):
        """Stop all playing clips."""
        self._client.send("/live/song/stop_all_clips")

    # --- Tempo ---

    async def get_tempo(self) -> Optional[float]:
        """Get current tempo in BPM."""
        result = await self._client.send_and_wait("/live/song/get/tempo")
        if result:
            self._client.state.tempo = float(result[0])
            return self._client.state.tempo
        return None

    async def set_tempo(self, bpm: float):
        """Set tempo in BPM."""
        bpm = max(20.0, min(999.0, float(bpm)))  # Ableton's tempo range
        self._client.send("/live/song/set/tempo", bpm)
        self._client.state.tempo = bpm

    # --- Play State ---

    async def is_playing(self) -> Optional[bool]:
        """Check if transport is playing."""
        result = await self._client.send_and_wait("/live/song/get/is_playing")
        if result:
            self._client.state.playing = bool(result[0])
            return self._client.state.playing
        return None

    # --- Metronome ---

    async def get_metronome(self) -> Optional[bool]:
        """Get metronome state."""
        result = await self._client.send_and_wait("/live/song/get/metronome")
        return bool(result[0]) if result else None

    async def set_metronome(self, enabled: bool):
        """Enable/disable metronome."""
        self._client.send("/live/song/set/metronome", int(enabled))

    # --- Loop ---

    async def get_loop(self) -> Optional[bool]:
        """Get loop state."""
        result = await self._client.send_and_wait("/live/song/get/loop")
        return bool(result[0]) if result else None

    async def set_loop(self, enabled: bool):
        """Enable/disable loop."""
        self._client.send("/live/song/set/loop", int(enabled))

    async def get_loop_start(self) -> Optional[float]:
        """Get loop start position in beats."""
        result = await self._client.send_and_wait("/live/song/get/loop_start")
        return float(result[0]) if result else None

    async def set_loop_start(self, beats: float):
        """Set loop start position in beats."""
        self._client.send("/live/song/set/loop_start", float(beats))

    async def get_loop_length(self) -> Optional[float]:
        """Get loop length in beats."""
        result = await self._client.send_and_wait("/live/song/get/loop_length")
        return float(result[0]) if result else None

    async def set_loop_length(self, beats: float):
        """Set loop length in beats."""
        self._client.send("/live/song/set/loop_length", float(beats))

    # --- Position ---

    async def get_current_time(self) -> Optional[float]:
        """Get current song position in beats."""
        result = await self._client.send_and_wait("/live/song/get/current_song_time")
        return float(result[0]) if result else None

    async def set_current_time(self, beats: float):
        """Set current song position in beats."""
        self._client.send("/live/song/set/current_song_time", float(beats))

    async def jump_by(self, beats: float):
        """Jump song position by specified beats (positive or negative)."""
        self._client.send("/live/song/jump_by", float(beats))

    # --- Recording ---

    async def get_record_mode(self) -> Optional[bool]:
        """Get session record mode."""
        result = await self._client.send_and_wait("/live/song/get/record_mode")
        return bool(result[0]) if result else None

    async def set_record_mode(self, enabled: bool):
        """Enable/disable session record mode."""
        self._client.send("/live/song/set/record_mode", int(enabled))

    # --- Undo/Redo ---

    async def undo(self):
        """Undo last action."""
        self._client.send("/live/song/undo")

    async def redo(self):
        """Redo last undone action."""
        self._client.send("/live/song/redo")
