# TR-AIS — AI Drum Pattern Generator for Roland TR-8S

## Vision

TR-AIS is a natural language drum pattern generator that controls a Roland TR-8S drum machine via USB MIDI. The core concept: **the AI is a band member, not a vending machine.**

### The Personality Layer

The system builds a persistent "musical personality" that learns from every interaction:

- **Who the artist is** — genres, instruments, style preferences
- **What they like** — patterns accepted, positive feedback signals
- **What they hate** — patterns rejected, negative feedback signals  
- **Their vocabulary** — what "punchy" or "fat" means to THIS artist
- **Musical memory** — saved patterns recallable by name

This context is assembled and injected into every Claude request, making the AI feel like a session drummer who's worked with the artist for years. The moat is accumulated personality data — after months of use, switching tools feels like losing a bandmate.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User                                       │
│                    "Make it groovier, more like Tuesday"                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           main.py (FastAPI)                             │
│  1. Check for personality commands (save/recall/I hate X)               │
│  2. Build Claude messages with current pattern context                  │
│  3. Call generator.generate() with personality injection                │
│  4. Record feedback, update personality                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────┐
│    personality_engine.py      │   │     pattern_generator.py          │
│  ───────────────────────────  │   │  ─────────────────────────────    │
│  • Artist profile             │──▶│  System prompt + personality      │
│  • Learned preferences        │   │  context assembled here           │
│  • Vocabulary mappings        │   │                                   │
│  • Musical memories           │   │  Claude Sonnet 4 API call         │
│  • Feedback history           │   │                                   │
└───────────────────────────────┘   └───────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────────┐
                                    │        midi_engine.py             │
                                    │  ─────────────────────────────    │
                                    │  Real-time MIDI sequencer         │
                                    │  Thread-based, sub-ms timing      │
                                    │  Swing support                    │
                                    └───────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────────┐
                                    │         Roland TR-8S              │
                                    │         (USB MIDI)                │
                                    └───────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI server, WebSocket, session management, feedback tracking |
| `personality_engine.py` | Learns preferences, stores memories, assembles Claude context |
| `pattern_generator.py` | Claude API integration with personality injection |
| `midi_engine.py` | Real-time MIDI sequencer with swing |
| `static/index.html` | Web UI (chat, grid, controls) |
| `personality.json` | Persisted personality data |
| `sessions.json` | Persisted session data |

## Hardware Setup

- **TR-8S**: USB-B to USB-C cable to MacBook Air
- **Driver**: Roland Ver.1.0.3 (Sonoma/Sequoia, works on Tahoe 26.2)
- **MIDI ports**: `TR-8S` (main), `TR-8S CTRL` (SysEx)
- **Channel**: 10 (index 9)

## TR-8S MIDI Note Map

| Inst | Note | | Inst | Note |
|------|------|-|------|------|
| BD | 36 | | CP | 39 |
| SD | 38 | | RS | 37 |
| CH | 42 | | RC | 51 |
| OH | 46 | | CC | 49 |
| LT | 43 | | MT | 47 |
| HT | 50 | | | |

## Pattern JSON Format

```json
{
  "bpm": 120,
  "swing": 25,
  "kit_suggestion": "909",
  "instruments": {
    "BD": {"steps": [127,0,0,0,127,0,0,0,127,0,0,0,127,0,0,0]},
    "SD": {"steps": [0,0,0,0,127,0,0,0,0,0,0,0,127,0,0,0]}
  }
}
```

## Personality Commands

These are handled directly without Claude API calls:

| Command | Example | Effect |
|---------|---------|--------|
| Save | `save this as the good shuffle` | Store to memory |
| Recall | `play the good shuffle` | Load from memory |
| Dislike | `I hate four-on-floor` | Add negative pref |
| Like | `I love ghost notes` | Add positive pref |
| Profile | `my name is Jimmy` | Update profile |
| Genre | `I make 80s ballads` | Add genre weight |

## API Endpoints

### Sessions

- `POST /api/sessions` — create session
- `GET /api/sessions` — list sessions
- `GET /api/sessions/{id}` — get session
- `DELETE /api/sessions/{id}` — delete session
- `POST /api/sessions/{id}/message` — send message, get pattern
- `POST /api/sessions/{id}/version/{n}` — switch to version N
- `POST /api/sessions/{id}/feedback` — record accept/reject

### Playback

- `POST /api/play` — start
- `POST /api/stop` — stop
- `PATCH /api/params` — update BPM/swing

### Personality

- `GET /api/personality` — view state
- `GET /api/personality/context` — see what Claude sees
- `POST /api/personality/profile` — update profile

### WebSocket

- `WS /ws` — real-time step position + state updates

## Feedback Flow

```
User hears pattern → Clicks 👍 or 👎 → 
POST /api/sessions/{id}/feedback {"feedback_type": "accepted"} →
personality_engine extracts features from pattern →
Updates preference weights →
Next Claude call includes learned preferences
```

## What Claude Sees (Example)

```
# WHAT YOU KNOW ABOUT THIS ARTIST

## About This Artist
Name: Jimmy
Producer who gravitates toward 80s ballads, blues, and pop.
Genre tendencies: 80s_ballad (80%), pop (70%), blues (60%)
Preferred tempo: 70-130 BPM

## Learned Preferences
LIKES:
  ✓ ghost notes snare (60%)
  ✓ swing 40 (75%)
DISLIKES:
  ✗ busy hats (80%)
  ✗ four on floor (90%)

## VOCABULARY
  "punchy" → more attack on kick, tighter decay
  "driving" → steady 8ths, NOT faster tempo

## SAVED PATTERNS
  - "the Tuesday groove" [blues, favorite]
```

## Artist Context (Jimmy)

- Likes: 80s ballads, blues, pop, jam-style music
- Dislikes: Patterns that feel like hardware demos
- Jams with: Friend who likes trip-hop
- Values: Groove over complexity

## Running

```bash
pip3 install -r requirements.txt
# Set ANTHROPIC_API_KEY in .env
python3 main.py
# Open http://localhost:8000
```

## Future Ideas

- Voice input (Whisper → Claude → MIDI)
- Hardware device (Raspberry Pi + USB-MIDI)
- Multi-bar patterns with fills
- CC parameter control
- SysEx internal sequencer programming
