# Building ChatM4L - Max for Live AI Assistant

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
2. Type: `node.script ai/main.js`
3. Place it below the v8 object

Note: Unlike v8, node.script doesn't support `@autowatch`. To reload during development, send it a `script reload` message.

## Step 5: Copy the Code Files

The v8 and node.script objects need to find their JavaScript files.

1. Save the device first (Cmd+S / Ctrl+S)
   - Save it somewhere like `~/Music/Ableton/User Library/Presets/MIDI Effects/Max MIDI Effect/ChatM4L.amxd`

2. Create a `code` folder next to the .amxd file:
   ```
   ChatM4L.amxd
   code/
     bridge.js           ← copy from m4l/code/bridge.js
     ai/
       main.js           ← copy from m4l/code/ai/main.js
       package.json      ← copy from m4l/code/ai/package.json
       config.js         ← copy from m4l/code/ai/config.js
       client.js         ← copy from m4l/code/ai/client.js
       sessions.js       ← copy from m4l/code/ai/sessions.js
       commands/         ← copy entire folder
       defaults/         ← copy entire folder
   ```

3. In Max, update the object paths if needed:
   - `v8 code/bridge.js @autowatch 1`
   - `node.script code/ai/main.js`

## Step 6: Install npm Dependencies

1. Lock the device (click the lock icon or press Cmd+E / Ctrl+E)
2. Click on the `node.script` object
3. In the Max Console, you should see messages from the script
4. Send this message to install dependencies:
   - Create a `[message]` object with: `script npm install`
   - Connect it to `node.script` inlet
   - Click the message box

This installs `@anthropic-ai/sdk` and `openai` into `code/ai/node_modules/`.

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

## Step 9: Presentation Mode

1. Switch to Presentation Mode (Cmd+Opt+E / Ctrl+Alt+E)
2. For each UI object, open Inspector and check **Include in Presentation**
3. Arrange the objects in a nice layout:

```
┌──────────────────────────────────────┐
│ ChatM4L                   [Status]   │
├──────────────────────────────────────┤
│                                      │
│  Chat History                        │
│  (scrollable area)                   │
│                                      │
├──────────────────────────────────────┤
│ [Chat Input              ] [Send]    │
└──────────────────────────────────────┘
```

4. Resize each object to fit the layout
5. Lock the patch (Cmd+E / Ctrl+E)

## Step 10: Configure Your API Key

ChatM4L uses a config file instead of a UI input. On first use:

1. Type `/createconfig` in the chat and press Enter
2. This creates your config at: `~/Library/Application Support/ChatM4L/`
3. Open the config file:
   - Run `/openconfig` to see the path
   - Open `config.json` in any text editor
4. Replace `YOUR_ANTHROPIC_API_KEY` with your actual key:
   ```json
   "anthropic": {
     "apiKey": "sk-ant-api03-...",
     ...
   }
   ```
5. Save the file
6. Type `/reload` in the chat to apply changes

## Step 11: Test It

1. Type something in the chat: "What's on this track?"
2. Hit Enter or click Send
3. Watch the Max Console for debug output
4. The response should appear in chat history

### Try These Commands

- `/help` - Show all available commands
- `/status` - Show current provider, model, and skills
- `/skills` - List available skills
- `/newchat` - Start a fresh conversation

## Configuration

Your config lives at `~/Library/Application Support/ChatM4L/`:

```
ChatM4L/
├── config.json         # API keys, provider, model selection
├── README.md           # Quick reference guide
├── core/
│   ├── system.md       # AI personality and instructions
│   └── user.md         # Your musical profile (edit this!)
├── skills/
│   ├── drums.md
│   ├── mixing.md
│   └── sound-design.md
└── sessions/           # Conversation history (auto-managed)
```

### User Profile

Edit `core/user.md` to tell ChatM4L about your musical style:
- Genres and influences
- Reference artists
- Sound preferences
- Hardware and plugins you use

This context is included in every prompt, making responses more relevant to your workflow.

### Multiple Providers

ChatM4L supports Anthropic, OpenAI, and local models (Ollama/LM Studio):

```json
{
  "activeProvider": "anthropic",
  "providers": {
    "anthropic": {
      "apiKey": "sk-ant-...",
      "models": { "default": "claude-sonnet-4-20250514" }
    },
    "openai": {
      "apiKey": "sk-...",
      "models": { "default": "gpt-4o" }
    },
    "ollama": {
      "apiKey": null,
      "baseUrl": "http://localhost:11434/v1",
      "models": { "default": "llama3" }
    }
  }
}
```

Set `"activeProvider"` to switch between them, then `/reload`.

### Skills

Skills are specialized prompts for different production tasks:

- `/drums` - Drum programming expertise
- `/mixing` - Mix engineering guidance
- `/sound-design` - Sound design techniques

Or use `/skill off` to return to the base personality.

Add custom skills by creating `.md` files in `skills/`.

## Troubleshooting

### "No config found"
- Run `/createconfig` to create your config
- Then edit the API key and run `/reload`

### "Invalid API key"
- Check that your API key is correct in `config.json`
- Make sure you're using the right provider (Anthropic keys start with `sk-ant-`)
- Run `/reload` after editing

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
- Run `/status` to verify configuration
- Try `/ping` (should return `pong`)

### Config not loading
- Config auto-loads when Ableton restarts
- Use `/reload` to reload after editing config.json
- Check Max Console for config loading errors

## File Structure

```
Your Ableton User Library/
└── Presets/
    └── MIDI Effects/
        └── Max MIDI Effect/
            └── ChatM4L/
                ├── ChatM4L.amxd
                └── code/
                    ├── bridge.js
                    └── ai/
                        ├── main.js
                        ├── package.json
                        ├── config.js
                        ├── client.js
                        ├── sessions.js
                        ├── commands/
                        │   ├── index.js
                        │   ├── help.js
                        │   ├── status.js
                        │   ├── newchat.js
                        │   ├── skills.js
                        │   ├── skill.js
                        │   ├── createconfig.js
                        │   ├── openconfig.js
                        │   └── reload.js
                        ├── defaults/
                        │   ├── config.json
                        │   ├── README.md
                        │   ├── core/
                        │   │   ├── system.md
                        │   │   └── user.md
                        │   └── skills/
                        │       ├── drums.md
                        │       ├── mixing.md
                        │       └── sound-design.md
                        └── node_modules/
```

## Next Steps

Once the basic device works:
1. Edit `core/user.md` with your musical profile
2. Explore `/skills` for specialized assistance
3. Try controlling device parameters: "Turn down the filter"
4. Try adding MIDI notes: "Add a C major chord"
5. Create your own skills in `skills/`
