# TR-AIS Architecture & Vision

## What We're Building

An AI assistant that can **safely** control Ableton Live at scale - 100+ tracks, complex routing, thousands of parameters - through natural language.

Think Claude Code, but for music production.

## Current State (Prototype)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   CLI       │─────▶│   Claude    │─────▶│  Executor   │
│  (trais)    │◀─────│   Engine    │◀─────│             │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                  │
                     ┌─────────────┐              │
                     │   Session   │◀─────────────┤
                     │    Cache    │              │
                     └──────┬──────┘              │
                            │                     │
                            ▼                     ▼
                     ┌─────────────────────────────────┐
                     │         AbletonClient           │
                     │            (OSC)                │
                     └──────────────┬──────────────────┘
                                    │
                                    ▼
                     ┌─────────────────────────────────┐
                     │      Ableton Live + AbletonOSC  │
                     └─────────────────────────────────┘
```

**What works:**
- Natural language → Ableton commands
- Track names, tempo, transport
- Basic mixing (volume, pan, mute, solo)
- Device parameter control

**What doesn't scale:**
- Full session state sent to Claude every time
- No undo/revert capability
- No change history
- Sequential OSC queries (slow)

---

## The Hard Problems

### 1. Context at Scale

**Problem:** A real session has 100 tracks × 10 devices × 50 parameters = 50,000 data points. Claude's context window can't hold this, and even if it could, it would be slow and expensive.

**Solution: Hierarchical Context**

```
Level 0: Summary
  "88 BPM, 100 tracks, 12 groups, playing"

Level 1: Track List
  "Drums (group, 8 tracks), Bass, Synths (group, 12 tracks)..."

Level 2: Track Detail
  "Drums/Kick: Operator → Compressor → EQ, volume -3dB, no automation"

Level 3: Device Detail
  "Operator: Osc1=sine, Osc2=saw, Filter=LP 2kHz, Env=fast attack..."
```

Claude starts at Level 0. If user says "adjust the kick", we drill into Level 2-3 for just that track.

### 2. Undo/Revert (Critical)

**Problem:** Claude Code can revert file changes. We can't revert Ableton changes.

**Solution: Change Ledger**

```python
class ChangeLedger:
    changes: list[Change]  # Ordered list of all changes

@dataclass
class Change:
    id: str
    timestamp: datetime
    action: str           # "set_track_volume"
    target: str           # "track:4"
    old_value: any        # 0.85
    new_value: any        # 0.5
    reverted: bool        # False
```

Before any change:
1. Query current value
2. Record in ledger
3. Make change
4. If fails or user says "undo", restore old value

User can say: "undo", "undo last 3 changes", "revert all changes from this session"

### 3. Session Topology

**Problem:** Ableton sessions have complex structure:
- Groups containing tracks
- Return tracks with sends
- Master chain
- Sidechains
- Racks with chains

**Solution: Session Model**

```python
@dataclass
class SessionModel:
    tempo: float
    master: MasterTrack
    returns: list[ReturnTrack]
    groups: list[GroupTrack]  # Each contains child tracks
    tracks: list[Track]       # Ungrouped tracks

    def find_by_name(self, name: str) -> Track | Group | Return
    def get_signal_flow(self, track: Track) -> list[Device]
    def get_routing(self, track: Track) -> dict  # input, output, sends
```

### 4. Real-time Sync

**Problem:** User can change things in Ableton directly. Our cache becomes stale.

**Solution: OSC Subscriptions**

AbletonOSC supports `/live/*/start_listen` - Ableton pushes changes to us.

```python
# Subscribe to all track volumes
for i in range(track_count):
    client.send("/live/track/start_listen/volume", i)

# Handler receives updates automatically
def on_volume_change(track_index, new_volume):
    cache.tracks[track_index].volume = new_volume
    ledger.record_external_change(...)
```

---

## Integration Options

### Option A: External Process (Current)
```
[CLI/Web] ──OSC──▶ [Ableton + AbletonOSC]
```
- ✅ Easy to develop
- ✅ Full Python ecosystem
- ❌ Separate window
- ❌ No UI in Ableton

### Option B: Max4Live Device
```
[M4L Device with Node.js] ──Live API──▶ [Ableton]
```
- ✅ UI inside Ableton
- ✅ Direct Live API access
- ❌ JavaScript, not Python
- ❌ Complex to debug

### Option C: Hybrid
```
[M4L UI] ──WebSocket──▶ [Python Backend] ──OSC──▶ [AbletonOSC]
```
- ✅ UI in Ableton
- ✅ Python for AI logic
- ⚠️ More moving parts

**Recommendation:** Stay with Option A for now. Web UI is fine. Don't prematurely optimize for in-Ableton integration.

---

## Roadmap: What's Next

### Phase 1: Undo System (High Priority)
Without undo, users won't trust the AI to make changes.

- [ ] Change ledger (record before/after)
- [ ] `undo` command in CLI
- [ ] `undo last N` support
- [ ] Show change history

### Phase 2: Smart Context
Make it work with large sessions.

- [ ] Hierarchical session model
- [ ] Query only relevant tracks
- [ ] Summarize for Claude
- [ ] Cache at multiple levels

### Phase 3: Real-time Sync
Keep cache fresh without polling.

- [ ] OSC subscriptions for changes
- [ ] Mark external changes in ledger
- [ ] Conflict detection

### Phase 4: Web UI
Better UX than CLI.

- [ ] Chat interface
- [ ] Session visualization
- [ ] Change history view
- [ ] Undo buttons

### Phase 5: Deep Integration
If needed.

- [ ] M4L companion device
- [ ] Or Electron app with tighter integration

---

## Key Insight

The prototype proves the concept works. The real work is:

1. **Trust** - Undo system so users feel safe
2. **Scale** - Smart context so it works on real sessions
3. **Speed** - Parallel queries, subscriptions, caching
4. **UX** - Web UI, not CLI

We're building Claude Code for Ableton. That's the bar.
