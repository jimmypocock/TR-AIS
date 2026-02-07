# Beat Machine (TR-AIS)

AI-powered drum pattern generator for Roland TR-8S.

This is the original TR-AIS implementation, now part of the larger Ableton AI Assistant project.

## What It Does

- Generate drum patterns from natural language ("give me an 80s ballad groove")
- Outputs MIDI to Roland TR-8S hardware in real-time
- Learns your preferences over time (personality system)
- Web interface with pattern visualization

## Quick Start

```bash
cd beat-machine
pip3 install -r requirements.txt
python3 main.py
```

Open http://localhost:8000

## Requirements

- Roland TR-8S connected via USB
- `ANTHROPIC_API_KEY` in `.env` file

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server, WebSocket, session management |
| `midi_engine.py` | Real-time MIDI sequencer with swing |
| `pattern_generator.py` | Claude API integration |
| `static/index.html` | Web UI |

## Pattern Format

```json
{
  "bpm": 120,
  "swing": 25,
  "instruments": {
    "BD": {"steps": [127,0,0,0,127,0,0,0,127,0,0,0,127,0,0,0]},
    "SD": {"steps": [0,0,0,0,127,0,0,0,0,0,0,0,127,0,0,0]}
  }
}
```

## Future

This module will eventually integrate with the larger Ableton AI Assistant, allowing:
- Send patterns to Ableton as MIDI clips
- Sync tempo with Ableton
- Coordinate with other AI-powered modules (melody, synths, etc.)
