# Ableton AI Assistant

An AI-powered production assistant that controls Ableton Live through natural language.

> **Note:** This project evolved from TR-AIS (a drum pattern generator for Roland TR-8S). The original beat-machine functionality is preserved in the `beat-machine/` directory.

## Vision

Talk to your DAW like a collaborator:

- *"I want a drum beat in 80s ballad style"* → Selects instrument, creates pattern, adjusts parameters
- *"More reverb on Track 3 when the swell hits"* → Understands arrangement, creates automation
- *"Make the bass more aggressive"* → Knows which plugin and parameters control "aggression"

## Current Status

**Foundation complete:**
- [x] Modular Ableton control via OSC (`backend/ableton/`)
- [x] Transport, tracks, and device parameter control
- [x] Verified working with Ableton Live 12
- [ ] Session state caching
- [ ] Claude AI integration
- [ ] Web UI

## Quick Start

### Prerequisites

- Ableton Live 11+ with [AbletonOSC](https://github.com/ideoforms/AbletonOSC) installed
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Clone and setup
git clone https://github.com/jimmypocock/TR-AIS.git
cd TR-AIS

# Create virtual environment
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY
```

### Install AbletonOSC

1. Download from [github.com/ideoforms/AbletonOSC](https://github.com/ideoforms/AbletonOSC)
2. Copy to `~/Music/Ableton/User Library/Remote Scripts/AbletonOSC/`
3. In Ableton: Preferences → Link/Tempo/MIDI → Control Surface → AbletonOSC
4. You should see "Listening for OSC on port 11000" in Ableton's status bar

### Test Connection

```bash
source .venv/bin/activate
python3 -c "
import asyncio
from backend.ableton import AbletonClient

async def test():
    client = AbletonClient()
    await client.connect()
    await client.transport.set_tempo(100)
    print('Check Ableton - tempo should be 100 BPM')
    client.disconnect()

asyncio.run(test())
"
```

## Project Structure

```
.
├── backend/
│   ├── ableton/           # Modular Ableton control
│   │   ├── client.py      # Connection + OSC
│   │   ├── transport.py   # play, stop, tempo
│   │   ├── tracks.py      # create, volume, pan
│   │   └── devices.py     # parameters
│   └── config.py
├── beat-machine/          # Original TR-AIS (drum patterns for TR-8S)
├── plugins/               # Plugin parameter profiles (TODO)
├── tests/
└── docs/
```

## Usage (Python API)

```python
from backend.ableton import AbletonClient

client = AbletonClient()
await client.connect()

# Transport
await client.transport.play()
await client.transport.set_tempo(120)

# Tracks
idx = await client.tracks.create_midi("Synth Lead")
await client.tracks.set_volume(idx, 0.8)
await client.tracks.set_pan(idx, -0.3)

# Devices
await client.devices.set_parameter(track=0, device=0, param=3, value=0.7)
params = await client.devices.get_parameter_names(track=0, device=0)

client.disconnect()
```

## Beat Machine (Legacy)

The original TR-AIS drum pattern generator is still available:

```bash
cd beat-machine
pip3 install -r requirements.txt
python3 main.py
```

Open http://localhost:8000 to generate drum patterns for Roland TR-8S via natural language.

## Development

```bash
# Run unit tests
pytest tests/unit/ -v

# Run with Ableton open
pytest tests/integration/ -v
```

## License

MIT
