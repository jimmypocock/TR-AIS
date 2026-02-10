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

## Phase 1: Claude Integration ✅

### Goal
User says "create a synth track at 95 BPM" → Claude understands → Ableton executes

### Components

#### 1. Claude Engine (`backend/claude_engine.py`) ✅

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

#### 2. Command Executor (`backend/executor.py`) ✅

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

### Option A: CLI (Fastest) ✅

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

## Phase 3: Session State Caching ✅

### Goal
AI knows what's in your Ableton session without asking every time.

### Components

#### Session Cache (`backend/session_cache.py`) ✅

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

## Phase 5: Session Cache Optimizations

### Problem
Current approach queries Ableton for full state on startup. For large sessions (100+ tracks), this is slow. Each OSC query can timeout (0.5s), so 100 tracks × 6 properties = 300 queries = potential 2.5 min worst case.

### Solutions (Priority Order)

#### 1. Local Cache Updates (Easy)
When WE make a change, update cache locally instead of re-querying Ableton.

```python
# After muting track 4
cache.state.tracks[4].muted = True  # Update locally, no OSC needed
```

- [ ] Executor updates cache after successful commands
- [ ] Cache has `update_track()` method for local changes

#### 2. Parallel Queries (Medium)
Use `asyncio.gather()` for independent queries instead of sequential.

```python
# Current: 6 sequential queries per track
name = await get_name(i)
volume = await get_volume(i)
# ...

# Better: All at once
name, volume, pan, mute, solo, arm = await asyncio.gather(
    get_name(i), get_volume(i), get_pan(i),
    get_mute(i), get_solo(i), get_arm(i)
)
```

- [ ] Parallel queries within each track
- [ ] Parallel queries across tracks (batch of N at a time)

#### 3. OSC Subscriptions (Medium-Hard)
AbletonOSC supports `/live/*/start_listen` - Ableton pushes changes to us.

```python
# Subscribe to track 0 volume changes
client.send("/live/track/start_listen/volume", 0)

# Now Ableton will send us messages when volume changes
# Handler updates cache automatically
```

- [ ] Subscribe to track property changes
- [ ] Subscribe to transport changes
- [ ] Subscribe to track add/delete
- [ ] Unsubscribe on disconnect

#### 4. Minimal Context for Claude (Easy)
Claude doesn't need full state for most commands. "Mute the drums" only needs track names.

```python
# Full state (current)
{"tempo": 88, "tracks": [{"name": "Drums", "volume": 0.85, "pan": 0, ...}]}

# Minimal state (faster)
{"tempo": 88, "track_names": ["Drums", "Bass", "Keys"]}
```

- [ ] `cache.to_minimal_dict()` for common commands
- [ ] Full state only when Claude asks for details

#### 5. Lazy Loading (Medium)
Only query what's needed. If Claude mentions "the drums", query just that track.

- [ ] Query track by name on-demand
- [ ] Cache individual tracks as they're accessed
- [ ] Background refresh for full state

---

## Priority Order

1. ~~**Claude Engine**~~ ✅ - Core intelligence
2. ~~**CLI**~~ ✅ - Fastest way to test
3. ~~**Session Cache**~~ ✅ - Makes AI smarter
4. **Undo System** - Critical for trust
5. **Cache Optimizations** - Scale to large sessions
6. **Web UI** - Better UX
7. **Plugin Profiles** - Deep control

---

## Alternative: Instrument Mode

See [INSTRUMENT_MODE.md](INSTRUMENT_MODE.md) for a different approach:

Instead of an AI that controls the entire session, what if it's a **M4L device that lives on a single track**?

- Context naturally scoped (one track, not 100)
- Fits Ableton's mental model (it's just a device)
- Multiple instances with different specializations
- Safer by design (can't mess with other tracks)

This could be:
- A simpler V1 product
- A parallel track alongside Producer Mode
- The "instrument" to Producer Mode's "conductor"

---

## Definition of Done (MVP)

- [x] Can say "create a track called Lead" → track appears in Ableton
- [x] Can say "set tempo to 90" → tempo changes
- [x] Can say "make track 1 quieter" → volume decreases
- [x] Shows what Claude is "thinking"
- [x] Works via CLI
- [ ] Works via web interface
