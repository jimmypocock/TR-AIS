# TR-AIS

An AI-powered assistant for Ableton Live. Talk to your DAW like a collaborator.

```
> mute the bass and set tempo to 95
[Thinking...] User wants to mute "AI Bass" (track 4) and change tempo
[OK] set_track_mute: track 4 muted
[OK] set_tempo: 95 BPM

Muted the AI Bass track and set the tempo to 95 BPM.
```

## Status

**Working prototype.** Core functionality proven, now focused on scale and safety.

| Feature | Status |
|---------|--------|
| Natural language → Ableton commands | ✅ |
| Transport control (play, stop, tempo) | ✅ |
| Track control (volume, pan, mute, solo) | ✅ |
| Device parameters | ✅ |
| Session state caching | ✅ |
| Undo/revert changes | ❌ TODO |
| Large session support (100+ tracks) | ❌ TODO |
| Web UI | ❌ TODO |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full vision and roadmap.

## Quick Start

### Prerequisites

- Ableton Live 11+ with [AbletonOSC](https://github.com/ideoforms/AbletonOSC)
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Anthropic API key

### Setup

```bash
git clone https://github.com/jimmypocock/TR-AIS.git
cd TR-AIS

# Create environment
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Add API key
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY=sk-ant-...
```

### Install AbletonOSC

1. Download from [github.com/ideoforms/AbletonOSC](https://github.com/ideoforms/AbletonOSC)
2. Copy to `~/Music/Ableton/User Library/Remote Scripts/AbletonOSC/`
3. In Ableton: Preferences → Link/Tempo/MIDI → Control Surface → AbletonOSC
4. Look for "Listening for OSC on port 11000" in status bar

### Run

```bash
./trais
```

Try:
- "create a synth track"
- "set tempo to 120"
- "mute the drums"
- "make track 2 louder"
- "state" (show session info)

## Project Structure

```
.
├── trais                  # CLI launcher
├── backend/
│   ├── ableton/           # OSC client for Ableton
│   ├── claude_engine.py   # Natural language → commands
│   ├── executor.py        # Commands → Ableton
│   ├── session_cache.py   # Session state mirror
│   └── cli.py             # REPL interface
├── m4l/                   # ChatM4L - Max for Live AI assistant
│   ├── ChatM4L.amxd       # The device
│   ├── code/              # Device code
│   ├── README.md          # ChatM4L documentation
│   └── BUILD.md           # Build instructions
├── docs/
│   ├── ARCHITECTURE.md    # Vision and roadmap
│   ├── ROADMAP.md         # Detailed task breakdown
│   └── SESSION-CACHING.md # How caching works
├── beat-machine/          # Original TR-AIS (drum patterns for TR-8S)
└── tests/
```

## ChatM4L

**[ChatM4L](m4l/README.md)** is a Max for Live device that brings AI directly into Ableton. No external server needed - just drop it on a track and chat.

Features:
- Context-aware (sees your tracks and plugins)
- Multi-provider (Anthropic, OpenAI, Ollama)
- Skills system (specialized modes for drums, mixing, etc.)
- Session memory (remembers per track)

See [m4l/README.md](m4l/README.md) for details.

## What's Next

1. **Undo system** - Track changes, allow revert (like Claude Code)
2. **Smart context** - Handle 100+ track sessions efficiently
3. **Web UI** - Chat interface with session visualization

## Origins

This project evolved from TR-AIS, a drum pattern generator for Roland TR-8S. That code is preserved in `beat-machine/`.

The project now has two main components:
- **TR-AIS CLI** (this README) - Python backend for Ableton control via OSC
- **ChatM4L** (`m4l/`) - Max for Live device for in-DAW AI chat

## License

MIT
