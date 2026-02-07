import mido
import time
import threading
from typing import Optional, Callable, List

# TR-8S default MIDI note assignments
NOTE_MAP = {
    "BD": 36,   # Bass Drum (C1)
    "SD": 38,   # Snare Drum (D1)
    "LT": 43,   # Low Tom (G1)
    "MT": 47,   # Mid Tom (B1)
    "HT": 50,   # Hi Tom (D2)
    "RS": 37,   # Rim Shot (C#1)
    "CP": 39,   # Hand Clap (D#1)
    "CH": 42,   # Closed Hi-Hat (F#1)
    "OH": 46,   # Open Hi-Hat (A#1)
    "CC": 49,   # Crash Cymbal (C#2)
    "RC": 51,   # Ride Cymbal (D#2)
}

MIDI_CHANNEL = 9  # Channel 10 in 1-indexed (standard drum channel)


class MIDIEngine:
    def __init__(self, port_name: Optional[str] = None):
        self.port_name: Optional[str] = None
        self.port = None
        self.pattern: Optional[dict] = None
        self.bpm: float = 120.0
        self.swing: float = 0.0  # 0-100
        self.playing: bool = False
        self.current_step: int = 0
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.on_step: Optional[Callable[[int], None]] = None

        # Connect to specified port or first available
        if port_name:
            self._open_port(port_name)
        else:
            available = self.list_devices()
            if available:
                self._open_port(available[0])

    @staticmethod
    def list_devices() -> List[str]:
        """List all available MIDI output devices."""
        return mido.get_output_names()

    def _open_port(self, port_name: str):
        """Open a MIDI port by name."""
        self.port = mido.open_output(port_name)
        self.port_name = port_name

    def switch_device(self, port_name: str) -> bool:
        """
        Switch to a different MIDI device.
        Cleanly stops playback, closes old port, opens new one, and restores state.
        Returns True on success, False on failure.
        """
        was_playing = self.playing
        current_pattern = self.pattern

        # Stop playback and close current port
        self.stop()
        if self.port:
            try:
                self.port.close()
            except Exception:
                pass
            self.port = None
            self.port_name = None

        # Open new port
        try:
            self._open_port(port_name)
        except Exception as e:
            # Try to reconnect to old device if switch failed
            raise RuntimeError(f"Could not connect to {port_name}: {e}")

        # Restore pattern and playback state
        if current_pattern:
            self.set_pattern(current_pattern)
            if was_playing:
                self.play()

        return True

    def set_pattern(self, pattern: dict):
        """Update the current pattern. Thread-safe."""
        with self._lock:
            self.pattern = pattern
            if "bpm" in pattern:
                self.bpm = float(pattern["bpm"])
            if "swing" in pattern:
                self.swing = float(pattern["swing"])
        print(f"🎵 Pattern set - BPM={self.bpm}, swing={self.swing}, instruments={list(pattern.get('instruments', {}).keys())}")

    def set_bpm(self, bpm: float):
        with self._lock:
            self.bpm = max(30.0, min(300.0, bpm))

    def set_swing(self, swing: float):
        with self._lock:
            self.swing = max(0.0, min(100.0, swing))

    def play(self):
        """Start the sequencer loop."""
        print(f"🎵 MIDIEngine.play() called - already playing={self.playing}, port={self.port_name}")
        if self.playing:
            return
        self.playing = True
        self.current_step = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"🎵 Sequencer thread started")

    def stop(self):
        """Stop the sequencer and send all notes off."""
        self.playing = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self.current_step = 0
        # All notes off
        if self.port:
            for note in NOTE_MAP.values():
                self.port.send(mido.Message("note_off", note=note, channel=MIDI_CHANNEL))

    def _loop(self):
        """Main sequencer loop — runs in a separate thread."""
        print(f"🔄 Loop started - port={self.port_name}, port_open={self.port is not None}")
        next_time = time.perf_counter()

        while self.playing:
            with self._lock:
                pattern = self.pattern
                bpm = self.bpm
                swing = self.swing

            if pattern is None:
                time.sleep(0.01)
                continue

            # Broadcast current step for UI visualization
            if self.on_step:
                try:
                    self.on_step(self.current_step)
                except Exception:
                    pass

            # Send MIDI notes for this step
            if self.port:
                instruments = pattern.get("instruments", {})
                for inst_name, inst_data in instruments.items():
                    if inst_name not in NOTE_MAP:
                        continue
                    steps = inst_data.get("steps", [])
                    if self.current_step < len(steps):
                        velocity = int(steps[self.current_step])
                        if velocity > 0:
                            self.port.send(
                                mido.Message(
                                    "note_on",
                                    note=NOTE_MAP[inst_name],
                                    velocity=min(127, max(1, velocity)),
                                    channel=MIDI_CHANNEL,
                                )
                            )

            # Calculate timing with swing
            step_duration = 60.0 / bpm / 4.0  # Duration of one 16th note

            # Swing: shifts every other 16th note later
            # swing_amount: 0 = straight, 0.33 = full triplet swing
            swing_amount = (swing / 100.0) * 0.33

            if self.current_step % 2 == 0:
                # Even step → odd step: longer gap (delay the off-beat)
                actual_duration = step_duration * (1.0 + swing_amount)
            else:
                # Odd step → even step: shorter gap (catch up)
                actual_duration = step_duration * (1.0 - swing_amount)

            next_time += actual_duration
            # Get step count from pattern (default 16 for backwards compatibility)
            step_count = 16
            instruments = pattern.get("instruments", {})
            if instruments:
                first_inst = next(iter(instruments.values()), {})
                step_count = len(first_inst.get("steps", [])) or 16
            self.current_step = (self.current_step + 1) % step_count

            # High-precision busy wait
            while time.perf_counter() < next_time:
                remaining = next_time - time.perf_counter()
                if remaining > 0.002:
                    time.sleep(0.0005)

    def send_test_note(self, instrument: str = "BD", velocity: int = 127):
        """Send a single test note."""
        if self.port and instrument in NOTE_MAP:
            self.port.send(
                mido.Message(
                    "note_on",
                    note=NOTE_MAP[instrument],
                    velocity=velocity,
                    channel=MIDI_CHANNEL,
                )
            )

    def close(self):
        self.stop()
        if self.port:
            self.port.close()
            self.port = None
            self.port_name = None