"""
Ableton Client - Core OSC connection and communication.

This is the main interface for communicating with Ableton Live via AbletonOSC.
It manages the connection, sends/receives OSC messages, and provides access
to sub-modules for transport, tracks, devices, etc.
"""

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

if TYPE_CHECKING:
    from .transport import TransportController
    from .tracks import TrackController
    from .devices import DeviceController


@dataclass
class AbletonConfig:
    """Configuration for Ableton connection."""
    host: str = "127.0.0.1"
    send_port: int = 11000  # AbletonOSC listens here
    receive_port: int = 11001  # AbletonOSC sends responses here
    timeout: float = 5.0  # Seconds to wait for response


@dataclass
class SessionState:
    """Mirrors the current state of the Ableton session."""
    connected: bool = False
    tempo: float = 120.0
    playing: bool = False
    recording: bool = False
    track_count: int = 0


class AbletonClient:
    """
    Main client for communicating with Ableton Live via AbletonOSC.

    Provides namespaced access to different aspects of Live:
    - client.transport - play, stop, tempo, etc.
    - client.tracks - create, volume, pan, etc.
    - client.devices - parameters, presets, etc.

    Usage:
        client = AbletonClient()
        await client.connect()

        await client.transport.play()
        await client.tracks.create_midi("Drums")
        await client.devices.set_parameter(0, 0, 3, 0.7)

        client.disconnect()
    """

    def __init__(self, config: AbletonConfig = None):
        self.config = config or AbletonConfig()
        self._osc_client: Optional[udp_client.SimpleUDPClient] = None
        self._osc_server: Optional[BlockingOSCUDPServer] = None
        self._server_thread: Optional[threading.Thread] = None

        self.state = SessionState()
        self._response_queue: dict[str, asyncio.Future] = {}
        self._dispatcher = Dispatcher()
        self._setup_dispatcher()

        # Controllers (initialized lazily)
        self._transport: Optional["TransportController"] = None
        self._tracks: Optional["TrackController"] = None
        self._devices: Optional["DeviceController"] = None

    def _setup_dispatcher(self):
        """Configure OSC message handlers."""
        self._dispatcher.set_default_handler(self._handle_response)
        self._dispatcher.map("/live/song/get/tempo", self._handle_tempo)
        self._dispatcher.map("/live/song/get/is_playing", self._handle_playing)
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

    def _handle_error(self, address: str, *args):
        """Handle error messages from AbletonOSC."""
        print(f"AbletonOSC Error: {args}")

    # --- Connection Management ---

    async def connect(self) -> bool:
        """
        Establish connection to Ableton Live via AbletonOSC.

        Returns True if connection successful, False otherwise.
        """
        try:
            # Create OSC client for sending
            self._osc_client = udp_client.SimpleUDPClient(
                self.config.host,
                self.config.send_port
            )

            # Create OSC server for receiving responses
            self._osc_server = BlockingOSCUDPServer(
                (self.config.host, self.config.receive_port),
                self._dispatcher
            )

            # Run server in background thread
            self._server_thread = threading.Thread(
                target=self._osc_server.serve_forever,
                daemon=True
            )
            self._server_thread.start()

            # Test connection by requesting tempo
            tempo = await self.transport.get_tempo()
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
        if self._osc_server:
            self._osc_server.shutdown()
        self.state.connected = False
        print("Disconnected from Ableton Live")

    @property
    def is_connected(self) -> bool:
        """Check if connected to Ableton."""
        return self.state.connected

    # --- OSC Communication (used by sub-controllers) ---

    async def send_and_wait(
        self,
        address: str,
        *args,
        response_address: str = None,
        timeout: float = None
    ) -> Optional[tuple]:
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
        if not self._osc_client:
            raise RuntimeError("Not connected to Ableton")

        response_addr = response_address or address
        timeout = timeout or self.config.timeout

        # Create future for response
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._response_queue[response_addr] = future

        # Send message
        self._osc_client.send_message(address, list(args) if args else [])

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout)
            return result
        except asyncio.TimeoutError:
            self._response_queue.pop(response_addr, None)
            return None

    def send(self, address: str, *args):
        """Send message without waiting for response."""
        if self._osc_client:
            self._osc_client.send_message(address, list(args) if args else [])

    # --- Sub-controllers (lazy initialization) ---

    @property
    def transport(self) -> "TransportController":
        """Access transport controls (play, stop, tempo, etc.)."""
        if self._transport is None:
            from .transport import TransportController
            self._transport = TransportController(self)
        return self._transport

    @property
    def tracks(self) -> "TrackController":
        """Access track controls (create, volume, pan, etc.)."""
        if self._tracks is None:
            from .tracks import TrackController
            self._tracks = TrackController(self)
        return self._tracks

    @property
    def devices(self) -> "DeviceController":
        """Access device controls (parameters, presets, etc.)."""
        if self._devices is None:
            from .devices import DeviceController
            self._devices = DeviceController(self)
        return self._devices
