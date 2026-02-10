# Instrument Mode: Track-Scoped AI

## Concept

Instead of an AI that controls the entire session ("Producer Mode"), what if the AI lives as a **device on a single track**?

```
┌─────────────────────────────────────────────────────┐
│  Track: AI Drums                                     │
├─────────────────────────────────────────────────────┤
│  [TR-AIS Device]                                     │
│  ┌─────────────────────────────────────────────────┐│
│  │ 💬 "make the kick punchier"                     ││
│  │                                                  ││
│  │ Knows: this track's devices, song tempo,        ││
│  │        basic session context                     ││
│  │                                                  ││
│  │ Controls: only this track                        ││
│  └─────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────┤
│  [Drum Rack] → [Compressor] → [EQ Eight]            │
└─────────────────────────────────────────────────────┘
```

## Why This Makes Sense

### 1. Context Naturally Scoped
- Only this track's devices and parameters
- Not 100 tracks × 10 devices × 50 parameters
- Fits easily in Claude's context window

### 2. Fits Ableton's Mental Model
- Users are used to putting instruments/effects on tracks
- It's just another device in the chain
- Drag and drop, no external apps

### 3. Multiple Specialized Instances
- AI on drums track: knows drum patterns, compression, punch
- AI on bass track: knows synthesis, sidechain, low-end
- AI on vocal track: knows EQ, de-essing, reverb
- Each can have different personalities/expertise

### 4. Safer by Design
- Can't accidentally delete tracks
- Can't mess with other parts of the session
- Scope is limited = less can go wrong
- Easier to undo (only affects one track)

### 5. M4L is Natural Fit
- Max4Live device has direct access to its track via Live API
- No OSC round-trips for local track info
- UI lives inside Ableton

## What It Knows

| Scope | Data | Purpose |
|-------|------|---------|
| Song | Tempo, key, time signature, playing state | Musical context |
| Session | Track names, group structure (summary only) | Know what else exists |
| This Track | All devices, all parameters, clips, automation | Full control |
| Neighbors | Adjacent tracks (optional) | "duck under the kick" |

## What It Controls

- ✅ This track's devices and parameters
- ✅ This track's mixer (volume, pan, sends)
- ✅ This track's clips and automation
- ❌ Other tracks (read-only awareness at most)
- ❌ Session structure (can't create/delete tracks)

## Implementation Options

### Option A: Pure M4L (JavaScript)
```
[M4L Device] ──Live API──▶ [This Track]
      │
      ▼
[Claude API call from JS]
```
- ✅ Simplest, everything in one place
- ❌ JavaScript, not Python
- ❌ Limited AI/ML libraries

### Option B: M4L + Python Backend
```
[M4L Device UI] ──WebSocket──▶ [Python Backend] ──Claude API──▶
      │                              │
      ▼                              ▼
[This Track via Live API]    [AI Processing]
```
- ✅ Python for AI logic
- ✅ UI in Ableton
- ❌ More moving parts
- ❌ Need to run backend separately

### Option C: M4L + Local Server (Hybrid)
```
[M4L Device] ──HTTP──▶ [Local FastAPI] ──Claude API──▶
      │                       │
      ▼                       ▼
[Track via Live API]   [Session Cache + AI]
```
- Backend could still have global session awareness
- M4L device is thin UI + track control
- Best of both worlds?

## Comparison: Producer Mode vs Instrument Mode

| Aspect | Producer Mode (Current) | Instrument Mode |
|--------|------------------------|-----------------|
| Scope | Entire session | Single track |
| Context size | Large (100+ tracks) | Small (1 track) |
| Integration | External CLI/Web | M4L device in Ableton |
| Capabilities | Create tracks, mix, arrange | Control this track only |
| Complexity | High | Lower |
| Safety | Needs undo system | Naturally scoped |
| Use case | "Mix the whole song" | "Make this synth warmer" |

## Could They Coexist?

Yes. They solve different problems:

- **Instrument Mode**: Fine-grained control of individual tracks
- **Producer Mode**: Session-wide decisions, arrangement, routing

A full system might have:
- TR-AIS devices on key tracks (drums, bass, leads)
- A Producer Mode for session-level commands
- They share context but have different scopes

## Next Steps (If Pursuing This)

1. **Prototype M4L device** - Simple chat UI that can read track devices
2. **Test Live API access** - Can we get device parameters easily?
3. **Bridge to Python** - WebSocket or HTTP to backend
4. **Limit scope deliberately** - Only this track, enforce boundaries

## Questions to Answer

- Can M4L JavaScript call Claude API directly? (probably yes, it's just HTTP)
- What's the latency like for Live API queries? (should be instant, no OSC)
- How do we handle the UI? (M4L has limited UI widgets)
- Do we need the Python backend at all for this mode?

---

## Summary

Instrument Mode is a simpler, safer, more Ableton-native approach:

> **"AI as a smart device on your track, not an omniscient producer"**

Worth exploring as V2 or parallel track. Current Producer Mode prototype proves the concept; Instrument Mode could be the product.
