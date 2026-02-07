# Ableton AI Assistant - Architecture Document

## Vision

An AI production assistant that lives alongside Ableton Live, understanding your session, your plugins, your arrangement, and executing complex musical intent through natural language.

**Examples of what it should handle:**
- "I want a drum beat in 80s ballad style" → Selects appropriate instrument, creates pattern, adjusts parameters
- "More reverb on Track 3 when the swell hits in the second chorus" → Understands arrangement, creates automation
- "Make the bass more aggressive" → Knows which track has bass, what plugin is on it, what parameters control "aggression"

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend (Web or Desktop)                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Chat UI with streaming "thinking" display                   │    │
│  │  Session state viewer (tracks, devices, arrangement)         │    │
│  │  Plugin browser / quick actions                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP/WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Python Backend (FastAPI)                         │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐     │
│  │ Claude API   │  │ Session      │  │ Plugin Profiles        │     │
│  │ (streaming   │  │ State Cache  │  │ (JSON mappings for     │     │
│  │  responses)  │  │ (mirrors     │  │  Ableton native,       │     │
│  │              │  │  Ableton)    │  │  Serum, Vital, etc.)   │     │
│  └──────────────┘  └──────────────┘  └────────────────────────┘     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Ableton Engine (OSC Client)                                   │   │
│  │ ─────────────────────────────────────────────────────────────│   │
│  │ • Query: Get session state (tracks, devices, clips, etc.)   │   │
│  │ • Execute: Create tracks, load plugins, set parameters      │   │
│  │ • Subscribe: Real-time updates when Ableton state changes   │   │
│  │ • Automate: Create/modify automation curves                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Modules (Extensible)                                          │   │
│  │ ─────────────────────────────────────────────────────────────│   │
│  │ • BeatMachine: TR-AIS drum pattern generation (MIDI out)    │   │
│  │ • MelodyEngine: Future melodic composition                   │   │
│  │ • SoundDesigner: Future synth patch generation               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ OSC (UDP)
                               │ Port 11000 (receive) / 11001 (send)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Ableton Live                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Max For Live Device (OSC Bridge)                              │   │
│  │ ─────────────────────────────────────────────────────────────│   │
│  │ Based on AbletonOSC or Respectrable                          │   │
│  │ • Exposes full Live Object Model via OSC                     │   │
│  │ • Bidirectional: receives commands, sends state changes      │   │
│  │ • Paths like: /live_set/tracks/0/devices/1/parameters/3     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │
│  │ Tracks │ │Devices │ │ Clips  │ │ Mixer  │ │Arrange │            │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Live Object Model Access

The M4L bridge exposes Ableton's internal API via OSC paths:

### Path Structure
```
live_set                          # Root of the session
  ├── tempo                       # BPM
  ├── tracks[N]                   # Track by index
  │     ├── name                  # Track name
  │     ├── mixer_device          # Volume, pan, sends
  │     │     ├── volume
  │     │     ├── panning
  │     │     └── sends[N]
  │     ├── devices[N]            # Plugins/instruments
  │     │     ├── name
  │     │     ├── parameters[N]   # Every knob/slider
  │     │     │     ├── name
  │     │     │     ├── value
  │     │     │     ├── min
  │     │     │     └── max
  │     │     └── ...
  │     └── clip_slots[N]         # Clips in session view
  │           └── clip
  │                 ├── name
  │                 ├── length
  │                 └── notes     # MIDI data
  ├── scenes[N]                   # Scene rows
  ├── cue_points[N]               # Arrangement markers
  └── ...
```

### Command Types
| Type | Example | Description |
|------|---------|-------------|
| `get` | `/live_set/tempo get` | Query a value |
| `set` | `/live_set/tempo set 120` | Modify a value |
| `call` | `/live_set/tracks/0 call delete_device 1` | Execute a function |

---

## Plugin Profile System

Each plugin gets a JSON profile mapping parameter indices to semantic names:

### Directory Structure
```
plugins/
  ableton/
    wavetable.json
    operator.json
    drum_rack.json
    compressor.json
    eq_eight.json
    reverb.json
  third_party/
    serum.json
    vital.json
    kontakt.json
    omnisphere.json
```

### Profile Format
```json
{
  "name": "Wavetable",
  "vendor": "Ableton",
  "type": "instrument",
  "categories": ["synth", "wavetable"],

  "parameters": {
    "0": {
      "name": "Osc 1 Wavetable Position",
      "semantic": ["wavetable_position", "timbre", "brightness"],
      "range": [0, 1],
      "default": 0.5
    },
    "12": {
      "name": "Filter 1 Frequency",
      "semantic": ["filter_cutoff", "brightness", "darkness"],
      "range": [20, 20000],
      "unit": "Hz",
      "default": 1000
    },
    "15": {
      "name": "Filter 1 Resonance",
      "semantic": ["resonance", "squelch", "acid"],
      "range": [0, 1],
      "default": 0
    }
  },

  "presets": {
    "init": "Default patch for starting point",
    "categories": ["bass", "pad", "lead", "keys", "pluck"]
  },

  "semantic_mappings": {
    "warmer": {"Filter 1 Frequency": -0.2, "Osc 1 Wavetable Position": -0.1},
    "brighter": {"Filter 1 Frequency": +0.3, "Osc 1 Wavetable Position": +0.2},
    "more_aggressive": {"Filter 1 Resonance": +0.3, "amp_attack": -0.5}
  }
}
```

### How AI Uses Profiles

When user says "make the pad warmer":
1. AI identifies pad track (from session state cache)
2. Looks up which device is the main instrument (e.g., Wavetable)
3. Loads Wavetable profile
4. Finds "warmer" in semantic_mappings
5. Generates OSC commands to adjust those parameters

---

## Session State Cache

The backend maintains a mirror of Ableton's state:

```python
session_state = {
    "tempo": 120,
    "playing": False,
    "tracks": [
        {
            "index": 0,
            "name": "Drums",
            "type": "midi",
            "armed": True,
            "devices": [
                {
                    "index": 0,
                    "name": "Drum Rack",
                    "type": "drum_rack",
                    "profile": "ableton/drum_rack",
                    "parameters": {...}
                }
            ],
            "clips": [...]
        },
        {
            "index": 1,
            "name": "Bass",
            "type": "midi",
            "devices": [
                {
                    "index": 0,
                    "name": "Serum",
                    "type": "vst",
                    "profile": "third_party/serum",
                    "parameters": {...}
                }
            ]
        }
    ],
    "arrangement": {
        "markers": [
            {"time": 0, "name": "Intro"},
            {"time": 16, "name": "Verse 1"},
            {"time": 48, "name": "Chorus 1"}
        ],
        "length": 192
    }
}
```

This cache is:
- Built on connect by querying Ableton
- Updated in real-time via OSC subscriptions
- Injected into Claude's context for every request

---

## Web vs Desktop Considerations

### Local Server Required Regardless

No matter what frontend we use, we need a local Python process for:
- Claude API calls
- OSC communication with Ableton
- Session state caching
- Plugin profile management

### Frontend Options

| Aspect | Web (Browser) | Desktop (Tauri) | Desktop (Electron) |
|--------|--------------|-----------------|-------------------|
| **Dev Speed** | Fastest | Medium | Medium |
| **Bundle Size** | N/A (browser) | ~5-10MB | ~150MB |
| **System Integration** | Limited | Full (hotkeys, tray) | Full |
| **Background Running** | No (needs tab) | Yes | Yes |
| **Cross-platform** | Yes | Yes | Yes |
| **Our Experience** | High | Low | Medium |
| **Upgrade Path** | → Tauri wrapper | Native | Native |

### Recommendation

**Start with Web, wrap in Tauri later.**

Reasons:
1. Web UI connects to same localhost backend either way
2. Faster to iterate during development
3. Can test on phone/tablet as bonus
4. Tauri can wrap our web UI with minimal changes when ready

---

## Implementation Phases

### Phase 1: Foundation (Current Focus)
- [ ] Set up AbletonOSC or Respectrable in Ableton
- [ ] Build Python OSC client (`ableton_engine.py`)
- [ ] Basic commands: connect, get session info, create track, set tempo
- [ ] Simple web UI with chat interface
- [ ] Claude integration with session context

### Phase 2: Core Intelligence
- [ ] Session state caching with real-time sync
- [ ] Ableton native plugin profiles (Wavetable, Operator, Drum Rack, etc.)
- [ ] Arrangement awareness (markers, sections)
- [ ] Automation curve generation

### Phase 3: Deep Integration
- [ ] Third-party plugin profiles (Serum, Vital, Kontakt)
- [ ] BeatMachine module (TR-AIS pattern generation)
- [ ] Desktop wrapper (Tauri)
- [ ] Voice input option

### Phase 4: Advanced Features
- [ ] Audio analysis for arrangement inference
- [ ] Multi-track operations ("make the whole mix punchier")
- [ ] Project templates and workflows
- [ ] Collaboration features

---

## File Structure (Proposed)

```
ableton-ai/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── ableton_engine.py       # OSC client for Ableton
│   ├── claude_engine.py        # Claude API integration
│   ├── session_cache.py        # Session state management
│   └── modules/
│       └── beat_machine/       # TR-AIS integration
│           ├── pattern_generator.py
│           ├── personality_engine.py
│           └── midi_engine.py
├── frontend/
│   └── (web UI files)
├── plugins/
│   ├── ableton/
│   │   └── *.json
│   └── third_party/
│       └── *.json
├── m4l/
│   └── AbletonAI.amxd          # Max For Live device
└── docs/
    └── *.md
```

---

## Key Dependencies

| Component | Library | Purpose |
|-----------|---------|---------|
| Backend | FastAPI | HTTP/WebSocket server |
| OSC | python-osc | Communicate with Ableton |
| AI | anthropic | Claude API |
| M4L Bridge | AbletonOSC or Respectrable | Expose Live Object Model |
| Desktop (future) | Tauri | Native app wrapper |

---

## Open Questions

1. **Project naming**: What do we call this? (AbletonAI, StudioAssistant, Maestro, etc.)
2. **TR-AIS fate**: Keep as separate project or fold into this as a module?
3. **M4L device**: Use existing (AbletonOSC) or build custom?
4. **Plugin profiles**: Start with how many? Just Ableton native?

---

## References

- [AbletonOSC](https://github.com/ideoforms/AbletonOSC) - OSC interface for Live
- [Respectrable](https://github.com/computersarecool/respectrable) - Bidirectional OSC M4L device
- [pylive](https://github.com/ideoforms/pylive) - Python wrapper for AbletonOSC
- [Live Object Model](https://docs.cycling74.com/userguide/m4l/live_api_overview/) - Cycling '74 docs
- [M4L Connection Kit](https://github.com/Ableton/m4l-connection-kit) - Official Ableton examples
