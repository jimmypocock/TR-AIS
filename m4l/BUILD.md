# Building the TR-AIS Max for Live Device

This guide walks through creating the M4L device from scratch in Ableton Live 12.2+.

## Prerequisites

- Ableton Live 12.2+ (includes Max 9 with v8 support)
- Max for Live (included in Suite, or add-on)
- The code files from this repo (`m4l/code/`)

## Step 1: Create the Device

1. Open Ableton Live
2. In the Browser sidebar, click **Max for Live**
3. Drag **Max MIDI Effect** onto any MIDI track
4. Click the device title bar, then click **Edit** (or press the edit button)

This opens the Max editor with a basic MIDI Effect template.

## Step 2: Clean Up the Template

1. Delete all the default objects (comments, tutorial text)
2. Keep only `[midiin]` and `[midiout]` - we need these for the device to work as a MIDI Effect
3. Connect them directly: `[midiin] → [midiout]` (MIDI passes through unchanged)

## Step 3: Add the v8 Object (Live API Bridge)

1. Press **N** to create a new object
2. Type: `v8 bridge.js @autowatch 1`
3. Place it in the patch

The `@autowatch 1` flag reloads the script when the file changes (useful for development).

## Step 4: Add the node.script Object (AI)

1. Press **N** to create a new object
2. Type: `node.script ai/main.js @autowatch 1`
3. Place it below the v8 object

## Step 5: Copy the Code Files

The v8 and node.script objects need to find their JavaScript files.

1. Save the device first (Cmd+S / Ctrl+S)
   - Save it somewhere like `~/Music/Ableton/User Library/Presets/MIDI Effects/Max MIDI Effect/TR-AIS.amxd`

2. Create a `code` folder next to the .amxd file:
   ```
   TR-AIS.amxd
   code/
     bridge.js       ← copy from m4l/code/bridge.js
     ai/
       main.js       ← copy from m4l/code/ai/main.js
       package.json  ← copy from m4l/code/ai/package.json
   ```

3. In Max, update the object paths if needed:
   - `v8 code/bridge.js @autowatch 1`
   - `node.script code/ai/main.js @autowatch 1`

## Step 6: Install npm Dependencies

1. Lock the device (click the lock icon or press Cmd+E / Ctrl+E)
2. Click on the `node.script` object
3. In the Max Console, you should see messages from the script
4. Send this message to install dependencies:
   - Create a `[message]` object with: `script npm install`
   - Connect it to `node.script` inlet
   - Click the message box

This installs `@anthropic-ai/sdk` into `code/ai/node_modules/`.

## Step 7: Add the UI Objects

### Chat History Display

1. Press **N** and type: `textedit`
2. Set these attributes in the Inspector (Cmd+I / Ctrl+I):
   - **Lines**: 12
   - **Read Only**: checked
   - **Word Wrap**: checked
   - **Font Size**: 11

### Chat Input

1. Press **N** and type: `textedit`
2. Set these attributes:
   - **Lines**: 2
   - **Key Mode**: 1 (Enter outputs buffer)
   - **Word Wrap**: checked
   - **Font Size**: 12

### Send Button

1. Press **N** and type: `live.text`
2. Set attributes:
   - **Mode**: Button
   - **Text**: "Send"

### API Key Input

1. Press **N** and type: `textedit`
2. Set attributes:
   - **Lines**: 1
   - **Parameter Mode Enable**: checked (saves with preferences)
3. Add a label: `[comment "API Key:"]`

### Set API Key Button

1. Press **N** and type: `live.text`
2. Set attributes:
   - **Mode**: Button
   - **Text**: "Set Key"

### Status Display

1. Press **N** and type: `textedit`
2. Set attributes:
   - **Lines**: 1
   - **Read Only**: checked
   - **Font Size**: 10

## Step 8: Wire Up the Patch

### Initialization
```
[live.thisdevice]
      |
      | (bang on load)
      ▼
[v8 code/bridge.js]
```

### Chat Input → v8
```
[textedit] (chat input)
      |
      | (outputs "text <message>" on Enter)
      ▼
[route text]
      |
      ▼
[prepend chat]
      |
      ▼
[v8 code/bridge.js]
```

### Send Button → trigger input
```
[live.text "Send"]
      |
      ▼
[bang]
      |
      ▼
[textedit] (sends current content)
```

### v8 ↔ node.script
```
[v8 code/bridge.js]
      | outlet 0 (to node)
      ▼
[node.script code/ai/main.js]
      | outlet (response/error)
      ▼
[route response error]
      |         |
      ▼         ▼
[prepend response]  [prepend error]
      |              |
      └──────┬───────┘
             ▼
      [v8 code/bridge.js]
```

### v8 → Chat History
```
[v8 code/bridge.js]
      | outlet 1 (history)
      ▼
[textedit] (chat history, readonly)
```

### v8 → Status
```
[v8 code/bridge.js]
      | outlet 2 (status)
      ▼
[textedit] (status display)
```

### API Key Flow
```
[textedit] (API key input)
      |
[route text]
      |
[t s b] (trigger: store symbol, then bang to clear)
      |     |
      |     ▼
      |   [set] → [textedit] (clear input after submit)
      ▼
[prepend setApiKey]
      |
      ▼
[v8 code/bridge.js]
```

## Step 9: Presentation Mode

1. Switch to Presentation Mode (Cmd+Opt+E / Ctrl+Alt+E)
2. For each UI object, open Inspector and check **Include in Presentation**
3. Arrange the objects in a nice layout:

```
┌──────────────────────────────────────┐
│ TR-AIS                    [Status]   │
├──────────────────────────────────────┤
│                                      │
│  Chat History                        │
│  (scrollable area)                   │
│                                      │
├──────────────────────────────────────┤
│ [Chat Input              ] [Send]    │
├──────────────────────────────────────┤
│ API Key: [••••••••••••••] [Set Key]  │
└──────────────────────────────────────┘
```

4. Resize each object to fit the layout
5. Lock the patch (Cmd+E / Ctrl+E)

## Step 10: Test It

1. Make sure you have your Anthropic API key ready
2. Paste it in the API Key field and click "Set Key"
3. Type something in the chat: "What's on this track?"
4. Hit Enter or click Send
5. Watch the Max Console for debug output
6. The response should appear in chat history

## Step 11: Save and Close

1. Save the device (Cmd+S)
2. Close the Max editor
3. The device is now ready to use!

## Troubleshooting

### "API key not configured"
- Make sure you clicked "Set Key" after entering your key
- Check Max Console for errors

### node.script errors
- Make sure npm packages are installed
- Check that `node_modules` exists in `code/ai/`
- Try: send `script npm install` to node.script again

### v8 errors
- Check that `bridge.js` path is correct
- Look for syntax errors in Max Console
- Make sure Live 12.2+ is installed (needs Max 9)

### No response from AI
- Check your API key is valid
- Check Max Console for network errors
- Try the `ping` command (should return `pong`)

## File Structure

```
Your Ableton User Library/
└── Presets/
    └── MIDI Effects/
        └── Max MIDI Effect/
            └── TR-AIS/
                ├── TR-AIS.amxd
                └── code/
                    ├── bridge.js
                    └── ai/
                        ├── main.js
                        ├── package.json
                        └── node_modules/
                            └── @anthropic-ai/
```

## Next Steps

Once the basic device works:
1. Try controlling device parameters: "Turn down the filter"
2. Try adding MIDI notes: "Add a C major chord"
3. Test with different plugins on the track
4. Customize the system prompt in `main.js` for your needs
