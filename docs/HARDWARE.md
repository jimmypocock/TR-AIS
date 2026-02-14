# Prototype Hardware Stack

An "Alexa for MIDI" — voice-controlled AI musician that speaks the language of any synth you plug it into. The beautiful thing is you've already validated the hard part (LLM → musically useful MIDI). Now it's just packaging.

**Cheapest path to working prototype (~$100-150):**

```
┌─────────────────────────────────────────────────────┐
│  Raspberry Pi 4/5 (or Pi Zero 2W for tiny)          │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐  │
│  │ USB Mic │  │ Speaker │  │ USB-MIDI Interface  │  │
│  └────┬────┘  └────┬────┘  └──────────┬──────────┘  │
│       │            │                  │             │
│       └────────────┴──────────────────┘             │
│                    │                                │
│              Python Stack                           │
│   Whisper (STT) → Claude API → mido (MIDI out)      │
│                    │                                │
│              WiFi for API calls                     │
└─────────────────────────────────────────────────────┘
                     │
                     ▼ MIDI OUT
            ┌────────────────┐
            │  Moog Sub-37   │
            │  TR-8S         │
            │  Any synth     │
            └────────────────┘
```

## Shopping List (Prototype)

| Part | Cost | Notes |
|------|------|-------|
| Raspberry Pi 5 (4GB) | ~$60 | Or Pi 4, or Zero 2W for smaller |
| USB-MIDI interface | ~$20 | Like the midiplus Tbox 2x2 |
| USB microphone | ~$15 | Or a speakerphone puck like Anker PowerConf |
| Small speaker | ~$10 | 3.5mm or USB, or use a Bluetooth speaker |
| Power supply + SD card | ~$25 | |
| **Total** | **~$130** | |

For a cleaner form factor later, you could use a **Pi HAT with MIDI ports** (like the Blokas Pisound ~$110) which gives you MIDI I/O + audio I/O in one board.

## Software Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ Voice Input  │───▶│   Claude     │───▶│   MIDI Engine    │   │
│  │  (Whisper)   │    │   (Sonnet)   │    │    (mido)        │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│         ▲                   │                     │             │
│         │                   ▼                     ▼             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Microphone  │    │ Voice Output │    │  MIDI OUT port   │   │
│  │              │    │   (TTS)      │    │                  │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Instrument Profiles                      │   │
│  │  - Moog Sub-37 (mono bass/lead, CC mappings)             │   │
│  │  - Roland TR-8S (drums, note map we built)               │   │
│  │  - Generic Poly Synth (chords, pads)                     │   │
│  │  - Generic Mono Synth (bass, lead)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components to Build

### 1. Wake Word + Voice Capture

```python
# Option A: Always listening with wake word ("Hey Maestro")
# Option B: Push-to-talk button (simpler, more reliable)

# Use OpenAI Whisper (runs locally on Pi, or use API for speed)
import whisper
model = whisper.load_model("base")  # "tiny" for faster on Pi
result = model.transcribe("recording.wav")
```

### 2. Instrument Profiles

```python
PROFILES = {
    "moog_sub37": {
        "type": "mono_synth",
        "midi_channel": 1,
        "note_range": (24, 96),  # C1 to C7
        "cc_map": {
            "filter_cutoff": 74,
            "resonance": 71,
            "osc_mix": 9,
        },
        "context": "Moog Sub-37 analog mono synth. Fat basses, screaming leads. One note at a time."
    },
    "tr8s": {
        "type": "drum_machine",
        "midi_channel": 10,
        "note_map": {"BD": 36, "SD": 38, ...},  # What we built
        "context": "Roland TR-8S drum machine with 808/909/707/606 sounds."
    },
    "generic_poly": {
        "type": "poly_synth",
        "midi_channel": 1,
        "note_range": (36, 84),
        "context": "Polyphonic synthesizer. Can play chords, pads, arpeggios."
    }
}
```

### 3. Voice Output (TTS)

```python
# Options (fast → slow, cloud → local):
# 1. OpenAI TTS API (best quality, ~$0.015/1K chars)
# 2. ElevenLabs (very natural)
# 3. Piper TTS (runs locally on Pi, free, decent quality)
# 4. espeak (robotic but instant, built into Pi)
```

### 4. Interaction Modes

The device could support multiple modes:

- **Sequence mode**: "Create a driving bassline in E minor" → generates looping MIDI sequence
- **Real-time mode**: "Play ascending arpeggios" → streams MIDI as you talk
- **Theory helper**: "What chords go with this melody?" → listens to MIDI input, analyzes, speaks answer
- **Learning mode**: "Teach me the blues scale in A" → plays notes, explains

## Development Path

**Phase 1: Laptop Prototype (This Week)**
Build it on your Mac first, just like TR-AIS. USB mic, USB-MIDI out to your Sub-37 or TR-8S. Validate the voice → Claude → MIDI loop works before touching hardware.

```bash
~/Projects/MaestroMIDI/
├── main.py
├── voice_input.py      # Whisper integration
├── voice_output.py     # TTS
├── midi_engine.py      # Reuse from TR-AIS
├── instruments/
│   ├── profiles.py
│   ├── moog_sub37.py
│   ├── tr8s.py
│   └── generic.py
└── CLAUDE.md
```

**Phase 2: Raspberry Pi Port**
Once it works on Mac, port to Pi. Main challenges:

- Whisper is slow on Pi (use `tiny` model or hit API)
- Need to optimize for headless operation
- Add physical button for push-to-talk
- Auto-start on boot

**Phase 3: Enclosure + Polish**

- 3D print a case (or buy a Pi case with room for extras)
- Add status LEDs (listening, thinking, playing)
- Maybe a small OLED screen for feedback
- Physical knob for tempo/volume

**Phase 4: Product?**
If it's genuinely useful, there's a real product here. Musicians would pay $200-300 for a box that does this well.

---

Want me to scaffold out the laptop prototype code so you can test voice → MIDI on your Mac before committing to hardware?
