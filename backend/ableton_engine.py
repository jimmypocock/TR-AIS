"""
Ableton Engine - OSC Client for Ableton Live

This module provides the interface between our backend and Ableton Live
via AbletonOSC. It handles:
- Connection management
- Sending OSC commands (get/set/call)
- Receiving responses and state updates
- Session state synchronization

Requires AbletonOSC to be installed and active in Ableton Live.
https://github.com/ideoforms/AbletonOSC
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer


@dataclass
class AbletonConfig:
    """Configuration for Ableton connection."""
    host: str = "127.0.0.1"
    send_port: int = 11000  # AbletonOSC listens here
    receive_port: int = 11001  # AbletonOSC sends responses here
    timeout: float = 5.0  # Seconds to wait for response


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
    devices: list = field(default_factory=list)


@dataclass
class SessionState:
    """Mirrors the current state of the Ableton session."""
    connected: bool = False
    tempo: float = 120.0
    playing: bool = False
    recording: bool = False
    tracks: list[Track] = field(default_factory=list)
    scenes: list[str] = field(default_factory=list)


class AbletonEngine:
    """
    OSC client for communicating with Ableton Live via AbletonOSC.

    Usage:
        engine = AbletonEngine()
        await engine.connect()

        # Query
        tempo = await engine.get_tempo()
        tracks = await engine.get_tracks()

        # Execute
        await engine.set_tempo(120)
        await engine.create_midi_track("Drums")

        # Cleanup
        engine.disconnect()
    """

    def __init__(self, config: AbletonConfig = None):
        self.config = config or AbletonConfig()
        self.client: Optional[udp_client.SimpleUDPClient] = None
        self.server: Optional[BlockingOSCUDPServer] = None
        self.server_thread: Optional[threading.Thread] = None

        self.state = SessionState()
        self._response_queue: dict[str, asyncio.Future] = {}
        self._dispatcher = Dispatcher()
        self._setup_dispatcher()

    def _setup_dispatcher(self):
        """Configure OSC message handlers."""
        # Default handler for all messages
        self._dispatcher.set_default_handler(self._handle_response)

        # Specific handlers for common messages
        self._dispatcher.map("/live/song/get/tempo", self._handle_tempo)
        self._dispatcher.map("/live/song/get/is_playing", self._handle_playing)
        self._dispatcher.map("/live/song/get/track_data", self._handle_track_data)
        self._dispatcher.map("/live/error", self._handle_error)

    def _handle_response(self, address: str, *args):
        """Generic response handler - resolves waiting futures."""
        if address in self._response_queue:
            future = self._response_queue.pop(address)
            if not future.done():
                future.set_result(args)

    def _handle_tempo(self, address: str, *args):
        """Handle tempo response."""
        if args:
            self.state.tempo = float(args[0])
        self._handle_response(address, *args)

    def _handle_playing(self, address: str, *args):
        """Handle playing state response."""
        if args:
            self.state.playing = bool(args[0])
        self._handle_response(address, *args)

    def _handle_track_data(self, address: str, *args):
        """Handle track data response."""
        # Track data comes as a list of values
        # Format varies - need to parse based on AbletonOSC spec
        self._handle_response(address, *args)

    def _handle_error(self, address: str, *args):
        """Handle error messages from AbletonOSC."""
        print(f"AbletonOSC Error: {args}")

    async def connect(self) -> bool:
        """
        Establish connection to Ableton Live via AbletonOSC.

        Returns True if connection successful, False otherwise.
        """
        try:
            # Create OSC client for sending
            self.client = udp_client.SimpleUDPClient(
                self.config.host,
                self.config.send_port
            )

            # Create OSC server for receiving responses
            self.server = BlockingOSCUDPServer(
                (self.config.host, self.config.receive_port),
                self._dispatcher
            )

            # Run server in background thread
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True
            )
            self.server_thread.start()

            # Test connection by requesting tempo
            tempo = await self.get_tempo()
            if tempo is not None:
                self.state.connected = True
                print(f"Connected to Ableton Live (tempo: {tempo} BPM)")
                return True
            else:
                print("Failed to connect - no response from AbletonOSC")
                return False

        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Clean up connection."""
        if self.server:
            self.server.shutdown()
        self.state.connected = False
        print("Disconnected from Ableton Live")

    async def _send_and_wait(self, address: str, *args,
                             response_address: str = None,
                             timeout: float = None) -> Optional[tuple]:
        """
        Send an OSC message and wait for response.

        Args:
            address: OSC address to send to
            *args: Arguments to send
            response_address: Address to listen for response (defaults to address)
            timeout: Seconds to wait (defaults to config timeout)

        Returns:
            Response arguments as tuple, or None on timeout
        """
        if not self.client:
            raise RuntimeError("Not connected to Ableton")

        response_addr = response_address or address
        timeout = timeout or self.config.timeout

        # Create future for response
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._response_queue[response_addr] = future

        # Send message
        self.client.send_message(address, args if args else [])

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout)
            return result
        except asyncio.TimeoutError:
            self._response_queue.pop(response_addr, None)
            return None

    def _send_fire_and_forget(self, address: str, *args):
        """Send message without waiting for response."""
        if self.client:
            self.client.send_message(address, args if args else [])

    # --- Query Methods ---

    async def get_tempo(self) -> Optional[float]:
        """Get current tempo in BPM."""
        result = await self._send_and_wait("/live/song/get/tempo")
        if result:
            self.state.tempo = float(result[0])
            return self.state.tempo
        return None

    async def get_is_playing(self) -> Optional[bool]:
        """Check if transport is playing."""
        result = await self._send_and_wait("/live/song/get/is_playing")
        if result:
            self.state.playing = bool(result[0])
            return self.state.playing
        return None

    async def get_track_count(self) -> Optional[int]:
        """Get number of tracks."""
        result = await self._send_and_wait("/live/song/get/num_tracks")
        return int(result[0]) if result else None

    async def get_track_names(self) -> Optional[list[str]]:
        """Get list of track names."""
        result = await self._send_and_wait(
            "/live/song/get/track_data",
            "name"
        )
        return list(result) if result else None

    async def get_session_info(self) -> dict:
        """Get comprehensive session information."""
        tempo = await self.get_tempo()
        playing = await self.get_is_playing()
        track_count = await self.get_track_count()
        track_names = await self.get_track_names()

        return {
            "tempo": tempo,
            "playing": playing,
            "track_count": track_count,
            "track_names": track_names,
        }

    # --- Transport Methods ---

    async def play(self):
        """Start playback."""
        self._send_fire_and_forget("/live/song/start_playing")
        self.state.playing = True

    async def stop(self):
        """Stop playback."""
        self._send_fire_and_forget("/live/song/stop_playing")
        self.state.playing = False

    async def set_tempo(self, bpm: float):
        """Set tempo in BPM."""
        self._send_fire_and_forget("/live/song/set/tempo", float(bpm))
        self.state.tempo = bpm

    # --- Track Methods ---

    async def create_midi_track(self, name: str = None, index: int = -1) -> Optional[int]:
        """
        Create a new MIDI track.

        Args:
            name: Track name (optional)
            index: Position to insert (-1 = end)

        Returns:
            Index of created track, or None on failure
        """
        # Create track
        self._send_fire_and_forget("/live/song/create_midi_track", index)

        # Wait a moment for track to be created
        await asyncio.sleep(0.1)

        # Get new track count to find the new track
        track_count = await self.get_track_count()
        new_index = track_count - 1 if track_count else None

        # Set name if provided
        if name and new_index is not None:
            self._send_fire_and_forget("/live/track/set/name", new_index, name)

        return new_index

    async def create_audio_track(self, name: str = None, index: int = -1) -> Optional[int]:
        """Create a new audio track."""
        self._send_fire_and_forget("/live/song/create_audio_track", index)
        await asyncio.sleep(0.1)
        track_count = await self.get_track_count()
        new_index = track_count - 1 if track_count else None

        if name and new_index is not None:
            self._send_fire_and_forget("/live/track/set/name", new_index, name)

        return new_index

    async def set_track_volume(self, track_index: int, volume: float):
        """Set track volume (0.0 to 1.0)."""
        self._send_fire_and_forget("/live/track/set/volume", track_index, float(volume))

    async def set_track_pan(self, track_index: int, pan: float):
        """Set track pan (-1.0 to 1.0)."""
        self._send_fire_and_forget("/live/track/set/panning", track_index, float(pan))

    # --- Device Methods ---

    async def get_device_name(self, track_index: int, device_index: int) -> Optional[str]:
        """Get device name."""
        result = await self._send_and_wait(
            "/live/device/get/name",
            track_index, device_index,
            response_address="/live/device/get/name"
        )
        return result[2] if result and len(result) > 2 else None

    async def get_device_parameters(self, track_index: int, device_index: int) -> Optional[list]:
        """Get all parameter names for a device."""
        result = await self._send_and_wait(
            "/live/device/get/parameters/name",
            track_index, device_index,
            response_address="/live/device/get/parameters/name"
        )
        # Response is: track_id, device_id, [names...]
        return list(result[2:]) if result and len(result) > 2 else None

    async def get_device_parameter_value(self, track_index: int, device_index: int,
                                          param_index: int) -> Optional[float]:
        """Get a device parameter value."""
        result = await self._send_and_wait(
            "/live/device/get/parameter/value",
            track_index, device_index, param_index,
            response_address="/live/device/get/parameter/value"
        )
        return float(result[3]) if result and len(result) > 3 else None

    async def set_device_parameter(self, track_index: int, device_index: int,
                                    param_index: int, value: float):
        """Set a device parameter value."""
        self._send_fire_and_forget(
            "/live/device/set/parameter/value",
            track_index, device_index, param_index, float(value)
        )


# --- Standalone Testing ---

async def test_connection():
    """Test basic connectivity."""
    engine = AbletonEngine()

    print("Connecting to Ableton...")
    connected = await engine.connect()

    if connected:
        print("\nSession Info:")
        info = await engine.get_session_info()
        for key, value in info.items():
            print(f"  {key}: {value}")

        print("\nTest: Set tempo to 100")
        await engine.set_tempo(100)
        await asyncio.sleep(0.5)
        tempo = await engine.get_tempo()
        print(f"  New tempo: {tempo}")

        print("\nTest: Create MIDI track")
        track_idx = await engine.create_midi_track("Test Track")
        print(f"  Created track at index: {track_idx}")

    engine.disconnect()


if __name__ == "__main__":
    asyncio.run(test_connection())
