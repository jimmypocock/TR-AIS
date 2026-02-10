# Session Caching

## Overview

SessionCache provides Claude with context about your Ableton session so it can understand commands like "mute the drums" without you specifying track numbers.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   You say:      │         │   SessionCache   │         │  Ableton Live   │
│ "mute the drums"│────────▶│   (in memory)    │◀───────▶│   (via OSC)     │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                    │
                                    ▼
                            ┌──────────────────┐
                            │  Claude sees:    │
                            │  {               │
                            │    tempo: 88,    │
                            │    tracks: [     │
                            │      {name: "Drums", index: 0},
                            │      {name: "Bass", index: 1}
                            │    ]             │
                            │  }               │
                            └──────────────────┘
```

## Flow

1. **On startup** → `cache.refresh()` queries Ableton for all tracks, devices, tempo, etc.
2. **Before each request** → Quick refresh to catch any changes you made in Ableton
3. **Claude receives** → JSON snapshot of session state with your message
4. **Claude responds** → "Mute track at index 0" (because it knows "Drums" = index 0)

## What's Cached

| Data | Cached | Notes |
|------|--------|-------|
| Tempo | ✅ | |
| Playing state | ✅ | |
| Recording state | ✅ | |
| Metronome | ✅ | |
| Track names | ✅ | |
| Track volume/pan | ✅ | |
| Track mute/solo/arm | ✅ | |
| Device names | ✅ | Per track |
| Device class names | ✅ | e.g., "Wavetable", "Compressor" |

## Persistence

- Cache lives in **memory only**
- Refreshed from Ableton on each request
- No disk storage - **Ableton IS the source of truth**
- Conversation history is NOT persisted between CLI sessions

## Helper Methods

```python
# Find track by name (case-insensitive, partial match)
track = cache.find_track_by_name("drums")  # Returns CachedTrack or None

# Find device by name, optionally within a track
result = cache.find_device_by_name("Wavetable")  # Returns (track, device) or None
result = cache.find_device_by_name("Reverb", track_name="Vocals")
```

---

## TODO: Not Yet Cached

These features would make Claude smarter but aren't implemented yet:

- [ ] **Clip contents** - What clips exist, their names, lengths
- [ ] **Clip slots** - Session view grid state
- [ ] **Automation** - Automation lanes and envelopes
- [ ] **Arrangement markers** - Locators and cue points
- [ ] **Plugin parameter values** - Current values of all device parameters (slow to query)
- [ ] **Send levels** - Current send amounts per track
- [ ] **Return tracks** - Return track names and devices
- [ ] **Master track** - Master track devices and settings
- [ ] **Scenes** - Scene names and states
- [ ] **Track grouping** - Group track relationships
- [ ] **Track colors** - Visual identification
- [ ] **Real-time updates** - OSC subscriptions for live state changes (currently polls on request)
