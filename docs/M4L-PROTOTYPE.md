# M4L AI Track Assistant - Prototype Design

## Overview

A Max for Live device that lives on a single track and provides AI-powered control via a chat interface. The AI can control plugins on the track, add MIDI clips, and eventually generate audio.

## Architecture

```
┌─────────────────────────── M4L Device ───────────────────────────┐
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                         UI Layer                             │ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │  Chat History (textedit readonly or jit.cellblock)      ││ │
│  │  │  - Scrollable                                            ││ │
│  │  │  - Shows user messages and AI responses                  ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │  Chat Input (textedit, keymode 1)         [Send Button] ││ │
│  │  │  - User types here, hits Enter to send                  ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    v8 Object (Bridge)                        │ │
│  │  - Has access to Live API                                    │ │
│  │  - Gets track context (devices, clips, state)                │ │
│  │  - Executes AI commands (set params, add notes, etc.)        │ │
│  │  - Communicates with node.script via dicts                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    node.script (AI)                          │ │
│  │  - Calls Claude API via @anthropic-ai/sdk                    │ │
│  │  - Processes user intent                                      │ │
│  │  - Returns structured commands                                │ │
│  │  - Runs in separate Node.js process                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Device Type

**MIDI Effect** - Recommended for JavaScript-based devices per [Adam Murray's tutorials](https://adammurray.link/max-for-live/v8-in-live/getting-started/). We're not processing audio, just controlling things.

The device sits in the track's device chain but doesn't alter MIDI flow (passes through).

## UI Components

### Chat Input
```
Object: textedit
Attributes:
  - keymode 1 (Enter outputs entire buffer)
  - lines 2 (multiline input)
  - wordwrap 1
  - Parameter Mode Enable (saves with Live Set)
```

### Chat History
```
Option A: textedit (simpler)
  - readonly 1
  - lines 10-15
  - wordwrap 1
  - Append new messages to buffer

Option B: jit.cellblock (more control)
  - Single column
  - Auto-scroll to bottom
  - readonly 1
  - Better for long conversations
```

### Send Button
```
Object: live.text
  - Button mode
  - Triggers same action as Enter key
```

## v8 Bridge Layer

The v8 object handles all Live API interaction. Key functions:

### Get Track Context
```javascript
// Get the track this device is on
function getTrackContext() {
    const track = new LiveAPI("this_device canonical_parent");

    return {
        name: track.get("name"),
        color: track.get("color"),
        volume: track.get("mixer_device volume"),
        pan: track.get("mixer_device panning"),
        muted: track.get("mute"),
        soloed: track.get("solo"),
        armed: track.get("arm"),
        devices: getDevices(track),
        clips: getClips(track)
    };
}

// Get all devices on track
function getDevices(track) {
    const devices = [];
    const count = track.get("devices").length / 2; // [id, id, ...] format

    for (let i = 0; i < count; i++) {
        const device = new LiveAPI(`${track.unquotedpath} devices ${i}`);
        devices.push({
            index: i,
            name: device.get("name"),
            class: device.get("class_name"),
            parameters: getParameters(device)
        });
    }
    return devices;
}
```

### Execute Commands
```javascript
// Set a device parameter
function setDeviceParameter(deviceIndex, paramIndex, value) {
    const param = new LiveAPI(
        `this_device canonical_parent devices ${deviceIndex} parameters ${paramIndex}`
    );
    param.set("value", value);
}

// Add MIDI notes to a clip
function addMidiNotes(clipSlotIndex, notes) {
    const clipSlot = new LiveAPI(
        `this_device canonical_parent clip_slots ${clipSlotIndex}`
    );

    // Create clip if empty
    if (!clipSlot.get("has_clip")) {
        clipSlot.call("create_clip", 4); // 4 beats
    }

    const clip = new LiveAPI(`${clipSlot.unquotedpath} clip`);
    clip.call("add_new_notes", { notes });
}
```

## node.script (Claude Integration)

```javascript
// main.js - Node for Max script
const maxAPI = require("max-api");
const Anthropic = require("@anthropic-ai/sdk");

const client = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY
});

// System prompt for track-scoped AI
const SYSTEM_PROMPT = `You are an AI assistant living on a single track in Ableton Live.
You can only control THIS track - its devices, parameters, and clips.
You receive context about the track state with each message.

When given a request, respond with:
1. "thinking": Your reasoning
2. "commands": Array of commands to execute
3. "response": What to tell the user

Commands you can issue:
- { "action": "set_parameter", "device": 0, "param": 3, "value": 0.7 }
- { "action": "add_notes", "clip_slot": 0, "notes": [...] }
- { "action": "set_volume", "value": 0.8 }
- { "action": "set_mute", "value": true }
`;

// Handle chat messages from Max
maxAPI.addHandler("chat", async (userMessage, trackContextJson) => {
    const trackContext = JSON.parse(trackContextJson);

    try {
        const response = await client.messages.create({
            model: "claude-sonnet-4-20250514",
            max_tokens: 1024,
            system: SYSTEM_PROMPT,
            messages: [{
                role: "user",
                content: `Track Context:\n${JSON.stringify(trackContext, null, 2)}\n\nUser: ${userMessage}`
            }]
        });

        const result = JSON.parse(response.content[0].text);
        maxAPI.outlet("response", JSON.stringify(result));

    } catch (error) {
        maxAPI.outlet("error", error.message);
    }
});

maxAPI.post("AI Track Assistant ready");
```

## Data Flow

```
1. User types "make it warmer" + hits Enter

2. textedit outputs to v8

3. v8:
   - Gets current track context (devices, params, clips)
   - Packages message + context
   - Sends to node.script

4. node.script:
   - Calls Claude API with message + context
   - Gets structured response
   - Sends back to v8

5. v8:
   - Parses commands
   - Executes each via Live API
   - Updates chat history

6. UI shows response in chat history
```

## File Structure

```
TR-AIS-M4L/
├── TR-AIS.amxd              # The M4L device
├── code/
│   ├── bridge.js            # v8 object code (Live API bridge)
│   └── ai/
│       ├── main.js          # node.script entry point
│       ├── package.json     # npm dependencies
│       └── node_modules/    # @anthropic-ai/sdk, etc.
└── README.md
```

## Requirements

- **Ableton Live 12.2+** (bundles Max 9 with v8 support)
- **Max for Live** (included in Live Suite, or add-on)
- **ANTHROPIC_API_KEY** environment variable

## Development Workflow

1. Create new MIDI Effect in Live
2. Edit in Max
3. Add UI objects (textedit, live.text)
4. Add v8 object, link to bridge.js
5. Add node.script, link to ai/main.js
6. Wire up the data flow
7. Test with simple commands
8. Iterate

## Phase 1 Capabilities

- [x] Chat UI (input + history)
- [ ] Get track context (name, devices, params)
- [ ] Send context + message to Claude
- [ ] Execute parameter changes
- [ ] Display responses

## Phase 2 Capabilities

- [ ] Add MIDI notes to clips
- [ ] Create new clips
- [ ] Semantic parameter control ("warmer", "brighter")

## Phase 3 Capabilities

- [ ] Session View clip triggering
- [ ] Arrangement View clip placement
- [ ] Multi-clip operations

## Phase 4 (Future)

- [ ] AI-generated audio (external service → audio file → clip)
- [ ] Pattern generation
- [ ] Sound design assistance

## References

- [Adam Murray - v8 in Live](https://adammurray.link/max-for-live/v8-in-live/) - Best tutorials
- [Cycling74 - Live Object Model](https://docs.cycling74.com/userguide/m4l/live_api_overview/)
- [Cycling74 - Node for Max API](https://docs.cycling74.com/nodeformax/api/)
- [textedit Reference](https://docs.cycling74.com/reference/textedit/)
- [Max Cookbook - Live API via JavaScript](https://music.arts.uci.edu/dobrian/maxcookbook/live-api-javascript)

## Open Questions

1. **API Key Storage**: How to securely store/access ANTHROPIC_API_KEY in M4L context?
   - Environment variable?
   - Config file?
   - User prompt on first use?

2. **State Persistence**: Should chat history persist with Live Set?
   - textedit with Parameter Mode Enable saves content
   - Or store in a dict that saves with set?

3. **Error Handling**: What happens when Claude API fails?
   - Timeout handling
   - Graceful degradation
   - Retry logic

4. **Latency UX**: Claude responses take 1-3 seconds
   - Show "thinking..." indicator
   - Stream responses?
