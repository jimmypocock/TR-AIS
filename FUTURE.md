# TR-AIS — AI Drum Pattern Generator for Roland TR-8S

## Vision

TR-AIS is a natural language drum pattern generator that controls a Roland TR-8S drum machine via USB MIDI. The core concept: **the AI is a band member, not a vending machine.** Users describe beats conversationally, and the system programs the TR-8S in real time. Each conversation is a collaborative refinement loop — building TOWARD the perfect pattern, like working with a session drummer in the studio.

The problem it solves: The TR-8S's built-in patterns feel like they're showcasing the hardware's capabilities rather than being musically useful for pop, ballad, blues, or jam-style contexts. This tool makes it instant to get a musically relevant beat going and iterate on it naturally.

## Architecture

```
Web UI (Chat Interface) → FastAPI backend → Claude API → Pattern JSON → MIDI Engine → TR-8S via USB
```

### Components

- **`main.py`** — FastAPI server with REST endpoints and WebSocket for real-time step position broadcasting. Manages sessions, routes messages to Claude, and coordinates playback.
- **`midi_engine.py`** — Real-time MIDI sequencer running in a separate thread. Sends note_on messages to TR-8S at precise timing with swing support. Uses busy-wait for sub-millisecond accuracy.
- **`pattern_generator.py`** — Claude API integration. Sends full conversation history to Claude with a carefully crafted system prompt. Claude returns both a natural language response and a structured JSON pattern.
- **`static/index.html`** — Single-page web app with chat interface, pattern grid visualization, playback controls (play/stop, BPM, swing), version navigation, and session management.
- **`sessions.json`** — Auto-persisted session data (conversations + pattern versions).

### Key Design Decisions

- **External sequencing approach**: Python sends MIDI notes to the TR-8S rather than programming the internal sequencer via SysEx. The TR-8S acts as a sound module. This was chosen for simplicity and immediate functionality.
- **Conversation-as-pattern model**: Each session IS a pattern evolution. The full conversation history is sent to Claude on each request so it knows exactly what's playing and can make targeted modifications. This prevents the "going off the rails" problem seen in other AI chat tools.
- **Current pattern injection**: When the user sends a refinement message, the current pattern JSON is injected as context so Claude modifies the existing pattern rather than generating from scratch.
- **Session versioning**: Every pattern Claude generates is stored as a version. Users can navigate back and forth between versions.
- **Phone accessible**: Server binds to 0.0.0.0:8000 so any device on the same WiFi can control it.

## Hardware Setup

- **TR-8S connection**: USB-B to USB-C direct cable to MacBook Air (macOS Tahoe 26.2)
- **Roland driver**: Ver.1.0.3 (Sonoma/Sequoia driver, works on Tahoe)
- **MIDI port names**: `TR-8S` (main MIDI), `TR-8S CTRL` (control/SysEx)
- **MIDI channel**: 10 (channel index 9)
- **Firmware**: TR-8S v3.0 (latest)

## TR-8S MIDI Note Map

| Instrument | Abbreviation | MIDI Note |
|-----------|-------------|-----------|
| Bass Drum | BD | 36 (C1) |
| Snare Drum | SD | 38 (D1) |
| Low Tom | LT | 43 (G1) |
| Mid Tom | MT | 47 (B1) |
| Hi Tom | HT | 50 (D2) |
| Rim Shot | RS | 37 (C#1) |
| Hand Clap | CP | 39 (D#1) |
| Closed Hi-Hat | CH | 42 (F#1) |
| Open Hi-Hat | OH | 46 (A#1) |
| Crash Cymbal | CC | 49 (C#2) |
| Ride Cymbal | RC | 51 (D#2) |

## Pattern JSON Format

```json
{
  "bpm": 120,
  "swing": 0,
  "kit_suggestion": "909",
  "instruments": {
    "BD": {"steps": [127,0,0,0,127,0,0,0,127,0,0,0,127,0,0,0]},
    "SD": {"steps": [0,0,0,0,127,0,0,0,0,0,0,0,127,0,0,0]},
    "CH": {"steps": [100,0,100,0,100,0,100,0,100,0,100,0,100,0,100,0]}
  }
}
```

- 16 steps per bar (16th notes)
- Each step: 0 = off, 1-127 = velocity
- Common velocities: 127 = accent, 100 = normal, 70 = medium, 45 = ghost note

## Musical Context (User Preferences)

- **Primary user**: Likes 80s style ballads, pop, jam-style music
- **Jam buddy**: Likes trippy stuff (trip hop, etc.)
- **Shared interest**: Blues
- **Pain point**: Default TR-8S patterns feel like hardware demos, not musically useful grooves

## Tech Stack

- Python 3.12 (via Anaconda)
- FastAPI + Uvicorn
- mido + python-rtmidi for MIDI
- Anthropic Python SDK (Claude Sonnet 4 for pattern generation)
- Vanilla JS frontend (no build step)
- macOS Tahoe 26.2 on MacBook Air

## API Endpoints

- `POST /api/sessions` — Create new session
- `GET /api/sessions` — List all sessions
- `GET /api/sessions/{id}` — Get session details
- `DELETE /api/sessions/{id}` — Delete session
- `POST /api/sessions/{id}/message` — Send chat message, get pattern back
- `POST /api/sessions/{id}/version/{n}` — Switch to pattern version N
- `POST /api/play` — Start playback
- `POST /api/stop` — Stop playback
- `PATCH /api/params` — Update BPM/swing in real time
- `WS /ws` — WebSocket for real-time step position + state updates

## Future Ideas (Not Implemented Yet)

- **Tap tempo**: Tap to set BPM while jamming, or sync to audio input
- **CC parameter control**: Send CC messages for per-instrument tuning, decay, filter, effects
- **PostgreSQL persistence**: Replace JSON file with proper DB for multi-user/long-term storage
- **Voice input**: Whisper → text → Claude → TR-8S
- **Pattern library/sharing**: Save and share favorite patterns
- **Multi-bar patterns**: Currently 1 bar (16 steps), could extend to 2-4 bars with fills. Need to think through how variable step counts work across different drum machines.
- **Device-agnostic support**: Make this work with any MIDI drum machine, not just TR-8S
- **Open source release**: Could become a community tool

## Running the Project

```bash
pip3 install -r requirements.txt
# Ensure .env has ANTHROPIC_API_KEY
python3 main.py
# Open http://localhost:8000
# Phone: http://<mac-ip>:8000
```
