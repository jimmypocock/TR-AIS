# AI Music Orchestrator - Vision Document

## Overview

This document explores the vision of an **AI Music Orchestrator** - a meta-tool that coordinates multiple specialized music AI tools (TR-AIS for drums, AbletonMCP for DAW control, future melody/synth tools) into a cohesive production workflow.

The key insight: TR-AIS feels like a **musician** (creative, pattern-focused), while AbletonMCP is more of a **controller** (technical, DAW-focused). An orchestrator layer could coordinate both, letting Claude act as a full producer.

---

## Protocol Comparison

| Protocol | Resolution | Transport | Advantages | Limitations |
|----------|-----------|-----------|------------|-------------|
| **MIDI CC** | 7-bit (0-127) | Serial/USB | Universal compatibility | Coarse resolution, steppy fades |
| **MIDI SysEx** | Arbitrary | Serial/USB | Device-specific deep control | No standard, complex |
| **OSC** | 32-bit float | Network/UDP | High resolution, human-readable, wireless | Less hardware support |
| **HUI** | 7-bit | MIDI | Pro Tools native | Deprecated, limited to 32 faders |
| **EUCON** | High | Ethernet | Full Pro Tools control | Avid proprietary |
| **ReaScript** | Native | In-process | 100% Reaper control | Reaper only |

**Recommendation:** OSC is the best general-purpose protocol for AI control - high resolution, network-native, and well-supported by modern DAWs.

---

## DAW-Specific Control Options

### Ableton Live (Best Option)
- **AbletonOSC** - Exposes entire Live Object Model via OSC ([GitHub](https://github.com/ideoforms/AbletonOSC))
- **pylive** - Python wrapper for AbletonOSC ([PyPI](https://pypi.org/project/pylive/))
- **AbletonMCP** - Already exists! Claude Desktop can control Ableton ([LobeHub](https://lobehub.com/mcp/fabian-tinkl-abletonmcp))
- Capabilities: Transport, tracks, clips, devices, plugins, mixing, MIDI notes, automation

### Reaper (Excellent Scriptability)
- **ReaScript API** - 756+ functions via Python/Lua/EEL ([Docs](https://www.reaper.fm/sdk/reascript/reascript.php))
- **Reaper MCP Server** - Full API exposed via MCP ([GitHub](https://github.com/shiehn/total-reaper-mcp))
- Capabilities: Everything - tracks, items, MIDI, FX, routing, automation, rendering

### Logic Pro (Limited)
- Control surfaces via MIDI CC
- SysEx requires Environment workarounds ([Apple Support](https://support.apple.com/guide/logicpro/work-with-sysex-messages-lgcp7714d233/mac))
- No official external API
- Best option: MIDI CC for automation, but no track/plugin creation

### Pro Tools (Restricted)
- **HUI Protocol** - Legacy, officially unsupported since PT11 ([Wikipedia](https://en.wikipedia.org/wiki/Human_User_Interface_Protocol))
- **EUCON** - Full control but proprietary hardware required
- No open API for external control

---

## What Could an "AI Producer" Control?

### Tier 1: Real-time Performance (Current TR-AIS)
- Trigger notes/drums via MIDI
- Adjust tempo, swing
- Pattern sequencing

### Tier 2: Mix Engineering
- Track volume/pan automation
- Send levels, routing
- Plugin parameter control (EQ, compression, effects)
- Mute/solo/arm tracks

### Tier 3: Arrangement & Composition
- Create/delete/duplicate tracks
- Create/move/edit clips
- MIDI note editing within clips
- Scene/section management
- Loop points, markers

### Tier 4: Full Production
- Load plugins/instruments by name
- Browse and load samples
- Render/export stems
- Project file management
- Sidechain routing setup

---

## Architecture Vision: The Orchestrator

### Current State: Separate Tools
```
┌─────────────────┐     ┌─────────────────┐
│    TR-AIS       │     │   AbletonMCP    │
│  (Drum Patterns)│     │  (DAW Control)  │
│   MIDI → TR-8S  │     │  OSC → Ableton  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───── Claude ──────────┘
              (coordinates manually)
```

### Future State: Orchestrator Architecture
```
                    ┌─────────────────────────┐
                    │   AI Music Orchestrator │
                    │    (Meta-coordinator)   │
                    └───────────┬─────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ TR-AIS  │ │ Melody  │ │ Synth   │ │Ableton  │ │ Reaper  │
   │ (Drums) │ │  Tool   │ │  Tool   │ │  MCP    │ │  MCP    │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │           │
   MIDI to TR-8S    │      MIDI to Synth   OSC        ReaScript
                    │
               MIDI to DAW
```

Each "plugin" is a specialized AI tool:
- **TR-AIS**: Drum pattern generation (creative, musician-like)
- **Melody Tool**: Melodic composition (future)
- **Synth Tool**: Sound design parameters (future)
- **AbletonMCP**: DAW arrangement & mixing (technical, controller-like)
- **ReaperMCP**: Alternative DAW support (future)

---

## Practical Example: AI as Co-Producer

User says: *"Add some reverb to the snare and create a 4-bar build with a filter sweep"*

AI could:
1. Identify snare track in Ableton
2. Load reverb plugin (Valhalla, stock Reverb)
3. Set reverb parameters (decay, wet/dry)
4. Create automation lane for filter cutoff
5. Draw automation curve (4-bar sweep)
6. Adjust TR-8S pattern to complement the build

---

## Immediate Setup: AbletonMCP + Claude Desktop

### Prerequisites
- Ableton Live Suite 10+ (you have this!)
- Python 3.8+
- UV package manager: `brew install uv`
- Claude Desktop app

### Step 1: Install AbletonMCP

**Option A - Automatic (recommended):**
```bash
npx -y @smithery/cli install @ahujasid/ableton-mcp --client claude
```

**Option B - Manual:**

Edit Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "AbletonMCP": {
      "command": "uvx",
      "args": ["ableton-mcp"]
    }
  }
}
```

### Step 2: Install Ableton Remote Script

1. Download `__init__.py` from [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp)
2. Create folder: `~/Music/Ableton/User Library/Remote Scripts/AbletonMCP/`
3. Place `__init__.py` in that folder
4. Restart Ableton Live
5. Go to **Preferences > Link/Tempo/MIDI**
6. Set Control Surface to **AbletonMCP**
7. Set Input/Output to **None**

### Step 3: Verify Connection

1. Restart Claude Desktop
2. You should see a hammer icon with "AbletonMCP" tools
3. Try: "Create a new MIDI track in Ableton"

### Available Tools via AbletonMCP

| Tool | Description |
|------|-------------|
| Get session info | Read tracks, clips, tempo |
| Create MIDI track | Add new MIDI tracks |
| Create audio track | Add new audio tracks |
| Add clip | Create clips in tracks |
| Add MIDI notes | Program notes in clips |
| Load instrument | Load Ableton instruments |
| Load effect | Add audio effects |
| Play/Stop | Transport control |
| Set tempo | Adjust BPM |

---

## Future Implementation Phases

### Phase 1: Test AbletonMCP Standalone
- Set up Claude Desktop with AbletonMCP
- Experiment with capabilities
- Identify gaps and limitations

### Phase 2: TR-AIS + Ableton Sync
- Sync BPM between TR-AIS and Live
- Consider routing TR-8S audio into Ableton
- Explore MIDI clock sync options

### Phase 3: Orchestrator Design
- Design unified prompt that understands both tools
- Create "production session" concept spanning hardware + software
- Build handoff patterns ("send this drum pattern to Ableton")

### Phase 4: Additional Plugins
- Melody generation tool (MIDI output)
- Synth parameter controller
- Sample browser/selector

---

## Key Dependencies

| Component | Library/Tool | Purpose |
|-----------|-------------|---------|
| OSC Client | `python-osc` | Send/receive OSC messages |
| Ableton Bridge | AbletonOSC | Live Object Model access |
| Reaper Bridge | ReaScript + MCP | Full DAW control |
| MIDI (fallback) | `mido` (existing) | Universal basic control |

---

## Risks & Considerations

1. **Latency**: OSC over network adds ~5-20ms; acceptable for mixing, not for live performance
2. **State sync**: DAW state can change externally; need polling or callbacks
3. **Plugin names**: AI needs to know what plugins are installed
4. **Complexity**: Full DAW control is orders of magnitude more complex than TR-8S
5. **User trust**: AI making destructive changes (delete tracks) needs confirmation UX

---

## Sources

- [AbletonOSC GitHub](https://github.com/ideoforms/AbletonOSC)
- [pylive on PyPI](https://pypi.org/project/pylive/)
- [AbletonMCP on LobeHub](https://lobehub.com/mcp/fabian-tinkl-abletonmcp)
- [Reaper ReaScript API](https://www.reaper.fm/sdk/reascript/reascript.php)
- [Reaper MCP Server](https://github.com/shiehn/total-reaper-mcp)
- [HUI Protocol Wikipedia](https://en.wikipedia.org/wiki/Human_User_Interface_Protocol)
- [OSC Introduction](https://mct-master.github.io/networked-music/2024/03/17/thomaseo-intro_to_OSC.html)
- [Logic Pro SysEx](https://support.apple.com/guide/logicpro/work-with-sysex-messages-lgcp7714d233/mac)
- [AI Music Production Tools 2025](https://pitchinnovations.com/blog/ai-music-production-tools-2025-best-daws-vst-plugins-studio-gear/)
- [Controlling Ableton with Python](https://sangarshanan.com/2025/02/25/connecting-python-with-ableton/)

---

## Summary

**Immediate next step:** Set up AbletonMCP with Claude Desktop to see what's possible. You already have Ableton Live Suite, so this is plug-and-play.

**Longer-term vision:** Build an orchestrator that coordinates:
- **TR-AIS** (musician brain - creative drum patterns)
- **AbletonMCP** (engineer brain - arrangement, mixing, effects)
- **Future tools** (melody, synth, samples)

The "AI as full producer" vision is technically feasible today. TR-AIS is a great foundation because it solves the hard problem (creative pattern generation). AbletonMCP solves the technical problem (DAW control). The missing piece is the orchestrator that knows when to use each tool and how to coordinate them into a cohesive production workflow.

---

## Quick Start Checklist

- [ ] Install UV: `brew install uv`
- [ ] Install AbletonMCP: `npx -y @smithery/cli install @ahujasid/ableton-mcp --client claude`
- [ ] Download Remote Script from GitHub
- [ ] Place in `~/Music/Ableton/User Library/Remote Scripts/AbletonMCP/`
- [ ] Configure Ableton Control Surface
- [ ] Restart Claude Desktop
- [ ] Test: "Create a new MIDI track called Drums"
