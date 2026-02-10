# Ableton AI Assistant - Roadmap

## Current State (Completed)

- [x] **Ableton OSC integration** (`backend/ableton/`)
  - Connect to Ableton via AbletonOSC
  - Transport: play, stop, tempo, loop, metronome
  - Tracks: create, delete, volume, pan, mute, solo, arm
  - Devices: get/set parameters
  - Verified working with Live 12

- [x] **Project structure**
  - Modular package design
  - Unit tests (14 passing)
  - Beat-machine preserved as module

---

## Phase 1: Claude Integration

### Goal
User says "create a synth track at 95 BPM" → Claude understands → Ableton executes

### Components

#### 1. Claude Engine (`backend/claude_engine.py`)

**What it does:**
- Takes user message + current session state
- Returns structured commands for Ableton

**Input:**
```python
{
    "message": "create a synth track and set tempo to 95",
    "session_state": {
        "tempo": 120,
        "tracks": [{"name": "Drums", "type": "midi"}]
    }
}
```

**Output:**
```python
{
    "thinking": "User wants a new synth track and tempo change...",
    "commands": [
        {"action": "create_midi_track", "params": {"name": "Synth"}},
        {"action": "set_tempo", "params": {"bpm": 95}}
    ],
    "response": "Created a synth track and set tempo to 95 BPM."
}
```

**How to test:**
```bash
python3 -c "
from backend.claude_engine import ClaudeEngine

engine = ClaudeEngine()
result = engine.process('create a drum track at 100 bpm', session_state={})
print(result)
"
```

**Success criteria:**
- Returns valid command structure
- Commands are executable by AbletonClient
- Response is conversational

#### 2. Command Executor (`backend/executor.py`)

**What it does:**
- Takes commands from Claude
- Executes them via AbletonClient
- Returns results

**Example:**
```python
async def execute(commands: list, client: AbletonClient):
    results = []
    for cmd in commands:
        if cmd["action"] == "set_tempo":
            await client.transport.set_tempo(cmd["params"]["bpm"])
            results.append({"success": True})
        elif cmd["action"] == "create_midi_track":
            idx = await client.tracks.create_midi(cmd["params"]["name"])
            results.append({"success": True, "track_index": idx})
    return results
```

---

## Phase 2: Interface

### Option A: CLI (Fastest)

Simple REPL for testing:

```bash
$ python3 -m backend.cli

Ableton AI Assistant
Connected to Ableton (tempo: 120 BPM, 4 tracks)

> create a bass track
Creating MIDI track "Bass"... done.

> set tempo to 85
Tempo set to 85 BPM.

> make track 2 louder
Set track 2 volume to 0.9.
```

**File:** `backend/cli.py`

**How to test:**
```bash
python3 -m backend.cli
```

**Success criteria:**
- Connects to Ableton on start
- Accepts natural language input
- Executes commands in Ableton
- Shows thinking/response

### Option B: Web UI (Better UX)

Chat interface like beat-machine:

**File:** `backend/main.py` + `static/index.html`

**Features:**
- WebSocket for real-time updates
- Shows session state (tracks, tempo)
- Chat history
- "Thinking" indicator

---

## Phase 3: Session State Caching

### Goal
AI knows what's in your Ableton session without asking every time.

### Components

#### Session Cache (`backend/session_cache.py`)

**What it does:**
- Queries Ableton on connect
- Caches: tracks, devices, tempo, playing state
- Updates in real-time via OSC listeners (future)

**Structure:**
```python
{
    "tempo": 95,
    "playing": False,
    "tracks": [
        {
            "index": 0,
            "name": "Drums",
            "type": "midi",
            "volume": 0.85,
            "pan": 0.0,
            "muted": False,
            "devices": [
                {"index": 0, "name": "Drum Rack", "class": "DrumGroupDevice"}
            ]
        }
    ]
}
```

**How to test:**
```bash
python3 -c "
import asyncio
from backend.ableton import AbletonClient
from backend.session_cache import SessionCache

async def test():
    client = AbletonClient()
    await client.connect()
    cache = SessionCache(client)
    await cache.refresh()
    print(cache.state)

asyncio.run(test())
"
```

**Success criteria:**
- Accurately reflects Ableton state
- Claude can reference tracks by name
- "Make the drums louder" works without specifying track number

---

## Phase 4: Plugin Profiles

### Goal
AI knows what "warmer" means for Wavetable vs Serum.

### Structure
```
plugins/
├── ableton/
│   ├── wavetable.json
│   ├── operator.json
│   └── compressor.json
└── third_party/
    └── serum.json
```

### Profile Format
```json
{
    "name": "Wavetable",
    "class_name": "InstrumentVector",
    "parameters": {
        "0": {"name": "Osc 1 Position", "semantic": ["brightness", "timbre"]},
        "12": {"name": "Filter Freq", "semantic": ["brightness", "warmth"]}
    },
    "semantic_mappings": {
        "warmer": {"12": -0.2},
        "brighter": {"12": +0.3, "0": +0.1}
    }
}
```

---

## Quick Start for Development

### 1. Activate environment
```bash
source .venv/bin/activate
```

### 2. Ensure Ableton + AbletonOSC running
Look for "Listening for OSC on port 11000"

### 3. Run tests
```bash
pytest tests/unit/ -v
```

### 4. Test connection
```bash
python3 -c "
import asyncio
from backend.ableton import AbletonClient

async def test():
    client = AbletonClient()
    await client.connect()
    print(f'Tempo: {await client.transport.get_tempo()}')
    client.disconnect()

asyncio.run(test())
"
```

---

## Priority Order

1. **Claude Engine** - Core intelligence
2. **CLI** - Fastest way to test
3. **Session Cache** - Makes AI smarter
4. **Web UI** - Better UX
5. **Plugin Profiles** - Deep control

---

## Definition of Done (MVP)

- [ ] Can say "create a track called Lead" → track appears in Ableton
- [ ] Can say "set tempo to 90" → tempo changes
- [ ] Can say "make track 1 quieter" → volume decreases
- [ ] Shows what Claude is "thinking"
- [ ] Works via CLI or web interface
