# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TR-AIS is a web application that uses Claude AI to generate drum patterns for the Roland TR-8S drum machine. Users describe beats in natural language, and the AI programs them in real-time via MIDI.

## Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the server (development)
python3 main.py

# Server runs at http://localhost:8000
```

## Architecture

**Backend (Python/FastAPI):**
- `main.py` - FastAPI server with WebSocket support for real-time communication
- `midi_engine.py` - Real-time 16-step MIDI sequencer with swing support
- `pattern_generator.py` - Claude API integration for pattern generation

**Frontend:**
- `static/index.html` - Single-page app with WebSocket client, pattern grid visualization, and chat UI

**Data flow:**
1. User sends natural language request via WebSocket
2. `PatternGenerator` calls Claude API with conversation history
3. Claude returns pattern as JSON (BPM, swing, instruments with 16-step velocity arrays)
4. `MIDIEngine` plays pattern via MIDI to TR-8S hardware
5. Frontend visualizes pattern and playhead position

## Key Technical Details

**MIDI:**
- Uses MIDI channel 10 (standard drums)
- 11 instruments: BD, SD, LT, MT, HT, RS, CP, CH, OH, CC, RC
- Note mapping in `NOTE_MAP` dict (e.g., BD=36, SD=38)
- High-precision timing with `perf_counter()` busy-wait loop

**Pattern format:**
```json
{
  "bpm": 120,
  "swing": 0,
  "instruments": {
    "BD": {"steps": [127,0,0,0,127,0,0,0,127,0,0,0,127,0,0,0]},
    "SD": {"steps": [0,0,0,0,127,0,0,0,0,0,0,0,127,0,0,0]}
  }
}
```

**Velocities:** 0=off, 40-60=ghost note, 100=normal, 127=accent

**Swing:** 0=straight, 20=subtle, 40=moderate, 60=heavy (applied as timing shift on off-beats)

## Environment

Requires `ANTHROPIC_API_KEY` in `.env` file. See `.env.example`.
