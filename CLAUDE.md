# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Ableton AI Assistant** - An AI-powered production assistant that controls Ableton Live through natural language. The system understands your session, plugins, and arrangement to execute complex musical intent.

### Vision
- "I want a drum beat in 80s ballad style" → Selects instrument, creates pattern, adjusts parameters
- "More reverb on Track 3 when the swell hits" → Understands arrangement, creates automation
- "Make the bass more aggressive" → Knows track, plugin, and which parameters control "aggression"

### Architecture Overview

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Frontend (Web) │────▶│ Python Backend  │────▶│   Ableton Live   │
│   Chat + State   │◀────│ FastAPI + Claude│◀────│   via AbletonOSC │
└──────────────────┘     └─────────────────┘     └──────────────────┘
```

## Directory Structure

```
.
├── backend/                 # Core AI + Ableton integration
│   ├── __init__.py
│   ├── config.py           # Environment configuration
│   ├── ableton/            # Modular Ableton control package
│   │   ├── __init__.py     # Exports AbletonClient
│   │   ├── client.py       # Connection, OSC, state management
│   │   ├── transport.py    # play, stop, tempo, loop, metronome
│   │   ├── tracks.py       # create, volume, pan, mute, solo, arm
│   │   └── devices.py      # parameters, presets, device info
│   ├── claude_engine.py    # Claude API integration (TODO)
│   ├── session_cache.py    # Session state management (TODO)
│   └── main.py             # FastAPI server (TODO)
│
├── beat-machine/           # TR-AIS drum pattern generator (legacy module)
│   ├── main.py             # Original TR-AIS server
│   ├── midi_engine.py      # MIDI sequencer for TR-8S
│   ├── pattern_generator.py # Claude drum pattern generation
│   ├── static/index.html   # Original web UI
│   └── requirements.txt    # Beat machine dependencies
│
├── plugins/                # Plugin parameter profiles
│   ├── ableton/           # Ableton native devices
│   └── third_party/       # Third-party VST profiles
│
├── tests/                  # Test suite
│   ├── unit/              # Tests without Ableton
│   ├── integration/       # Tests requiring Ableton
│   ├── mocks/             # Mock implementations
│   └── conftest.py        # Pytest fixtures
│
├── docs/                   # Documentation
│   ├── ABLETON-AI-ARCHITECTURE.md
│   └── ...
│
└── requirements.txt        # Project dependencies
```

## Setup

```bash
# Install uv (if not already installed)
brew install uv

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Commands

```bash
# Activate environment (do this first)
source .venv/bin/activate

# Run tests (unit only - no Ableton needed)
pytest tests/unit/ -v

# Run integration tests (requires Ableton + AbletonOSC)
pytest tests/integration/ -v

# Run the backend server (when implemented)
python3 -m backend.main

# Run legacy beat-machine
cd beat-machine && python3 main.py
```

## Key Components

### Backend (`backend/`)

**ableton/** - Modular OSC client for Ableton Live
- `client.py` - Connection management, OSC send/receive, session state
- `transport.py` - play, stop, tempo, loop, metronome, undo/redo
- `tracks.py` - create, delete, volume, pan, mute, solo, arm, sends
- `devices.py` - get/set parameters, device info, presets

Usage:
```python
from backend.ableton import AbletonClient

client = AbletonClient()
await client.connect()
await client.transport.set_tempo(120)
await client.tracks.create_midi("Drums")
await client.devices.set_parameter(0, 0, 3, 0.5)
```

**config.py** - Configuration management
- Loads from environment variables
- Ableton connection settings
- Claude API settings
- Plugin directory paths

### Beat Machine (`beat-machine/`)

The original TR-AIS implementation, now a module within the larger system.
- Generates drum patterns via Claude
- Outputs MIDI to Roland TR-8S hardware
- Has its own personality/preference learning system

### Plugin Profiles (`plugins/`)

JSON files mapping plugin parameters to semantic names:
```json
{
  "name": "Wavetable",
  "parameters": {
    "0": {"name": "Osc 1 Position", "semantic": ["wavetable_position", "timbre"]},
    "12": {"name": "Filter Freq", "semantic": ["filter_cutoff", "brightness"]}
  },
  "semantic_mappings": {
    "warmer": {"Filter Freq": -0.2},
    "brighter": {"Filter Freq": +0.3}
  }
}
```

## Development Process

### Build-Validate Cycle

Each feature follows:
1. **Build** - Implement the feature
2. **Unit Test** - Tests that run without Ableton
3. **Integration Test** - Tests with Ableton running
4. **Validation** - Demo it works before moving on

### Current Phase: Foundation

- [x] Project structure setup
- [x] Modular ableton/ package (client, transport, tracks, devices)
- [x] Test framework setup (14 unit tests)
- [x] AbletonOSC connection verified (Live 12)
- [ ] Session state caching
- [ ] Claude integration
- [ ] Basic web UI

## Dependencies

### Required for Backend
- `fastapi` - HTTP/WebSocket server
- `python-osc` - OSC communication with Ableton
- `anthropic` - Claude API
- `python-dotenv` - Environment configuration

### Required in Ableton
- **AbletonOSC** - M4L device exposing Live Object Model
  - Install from: https://github.com/ideoforms/AbletonOSC
  - Requires Ableton Live 11+ (works with Live 12)
  - Listens on port 11000, responds on 11001

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (with defaults)
ABLETON_HOST=127.0.0.1
ABLETON_SEND_PORT=11000
ABLETON_RECEIVE_PORT=11001
SERVER_PORT=8000
CLAUDE_MODEL=claude-sonnet-4-20250514
```

## Testing

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_ableton_engine.py -v

# Run with coverage
pytest tests/unit/ --cov=backend

# Run integration tests (Ableton must be running)
pytest tests/integration/ -v --ableton
```

## Key Technical Details

### OSC Protocol
- AbletonOSC exposes Live Object Model via OSC
- Paths follow LOM structure: `/live_set/tracks/0/devices/1/parameters/3`
- Message types: `get` (query), `set` (modify), `call` (execute function)

### Session State
The backend maintains a mirror of Ableton's state:
- Tracks (name, type, armed, devices)
- Devices (name, parameters)
- Transport (tempo, playing, recording)
- Arrangement (markers, sections)

This cache is:
- Built on connect by querying Ableton
- Updated in real-time via OSC subscriptions
- Injected into Claude's context for every request

### Plugin Parameter Access
Every device parameter accessible via:
```
/live_set/tracks/{N}/devices/{N}/parameters/{N}/get/value
/live_set/tracks/{N}/devices/{N}/parameters/{N}/set/value
```

Query parameter info: `get/name`, `get/min`, `get/max`

## Links

- [AbletonOSC](https://github.com/ideoforms/AbletonOSC) - OSC bridge for Ableton
- [pylive](https://github.com/ideoforms/pylive) - Python wrapper (optional)
- [Live Object Model](https://docs.cycling74.com/userguide/m4l/live_api_overview/) - Ableton API docs
