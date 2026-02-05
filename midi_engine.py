import mido
import time
import threading
from typing import Optional, Callable

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
    def __init__(self, port_name: str = "TR-8S"):
        self.port = mido.open_output(port_name)
        self.pattern: Optional[dict] = None
        self.bpm: float = 120.0
        self.swing: float = 0.0  # 0-100
        self.playing: bool = False
        self.current_step: int = 0
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.on_step: Optional[Callable[[int], None]] = None

    def set_pattern(self, pattern: dict):
        """Update the current pattern. Thread-safe."""
        with self._lock:
            self.pattern = pattern
            if "bpm" in pattern:
                self.bpm = float(pattern["bpm"])
            if "swing" in pattern:
                self.swing = float(pattern["swing"])

    def set_bpm(self, bpm: float):
        with self._lock:
            self.bpm = max(30.0, min(300.0, bpm))

    def set_swing(self, swing: float):
        with self._lock:
            self.swing = max(0.0, min(100.0, swing))

    def play(self):
        """Start the sequencer loop."""
        if self.playing:
            return
        self.playing = True
        self.current_step = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the sequencer and send all notes off."""
        self.playing = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self.current_step = 0
        # All notes off
        for note in NOTE_MAP.values():
            self.port.send(mido.Message("note_off", note=note, channel=MIDI_CHANNEL))

    def _loop(self):
        """Main sequencer loop — runs in a separate thread."""
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
            self.current_step = (self.current_step + 1) % 16

            # High-precision busy wait
            while time.perf_counter() < next_time:
                remaining = next_time - time.perf_counter()
                if remaining > 0.002:
                    time.sleep(0.0005)

    def send_test_note(self, instrument: str = "BD", velocity: int = 127):
        """Send a single test note."""
        if instrument in NOTE_MAP:
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
        self.port.close()