# ChatM4L

A Max for Live AI assistant that lives inside Ableton Live. Chat naturally to get production advice, control your session, and learn techniques in context.

## Features

- **Context-Aware** - Sees your tracks, plugins, and settings
- **Multi-Provider** - Works with Anthropic, OpenAI, or local models (Ollama/LM Studio)
- **Skills System** - Specialized modes for drums, mixing, sound design
- **Session Memory** - Remembers your conversation (per track, auto-rotates)
- **Config-Driven** - Customize prompts and add your own skills

## Quick Start

### Install

1. Copy `ChatM4L.amxd` to your Ableton User Library
2. Drag it onto any MIDI track
3. Type `/createconfig` to create your config
4. Edit `~/Library/Application Support/ChatM4L/config.json` with your API key
5. Type `/reload` to apply

### Use

Just type naturally:
- "What plugins are on this track?"
- "How do I get a punchy kick?"
- "Suggest some chord progressions in A minor"

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/status` | Show provider, model, and active skill |
| `/newchat` | Start a fresh conversation |
| `/skills` | List available skills |
| `/drums` | Activate drums skill |
| `/mixing` | Activate mixing skill |
| `/sound-design` | Activate sound design skill |
| `/skill off` | Deactivate skill |
| `/reload` | Reload config after editing |
| `/openconfig` | Show config folder path |
| `/createconfig` | Create/reset config from defaults |

## Configuration

Config lives at `~/Library/Application Support/ChatM4L/`:

```
ChatM4L/
├── config.json         # API keys, provider, model
├── core/
│   ├── system.md       # AI personality
│   └── user.md         # Your musical profile (edit this!)
├── skills/
│   ├── drums.md
│   ├── mixing.md
│   └── sound-design.md
└── sessions/           # Conversation history
```

### User Profile

Edit `core/user.md` to personalize ChatM4L:
- Your genres and influences
- Reference artists
- Sound preferences (drums, bass, synths)
- Hardware and plugins you use

This is included in every prompt so the AI understands your style.

### Providers

**Anthropic** (default):
```json
"anthropic": {
  "apiKey": "sk-ant-api03-...",
  "models": {
    "default": "claude-sonnet-4-20250514",
    "fast": "claude-3-5-haiku-20241022"
  }
}
```

**OpenAI**:
```json
"openai": {
  "apiKey": "sk-...",
  "models": { "default": "gpt-4o" }
}
```

**Local Models** (Ollama):
```json
"ollama": {
  "apiKey": null,
  "baseUrl": "http://localhost:11434/v1",
  "models": { "default": "llama3" }
}
```

Set `"activeProvider"` in config.json, then `/reload`.

### Custom Skills

Create a `.md` file in `skills/`:

```
skills/
└── my-skill.md
```

The skill auto-discovers. Activate with `/my-skill`.

### Settings

```json
"settings": {
  "maxHistory": 20,      // Messages to remember
  "sessionGapHours": 4,  // Hours before auto-new session
  "maxTokens": 1024      // Response length limit
}
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Ableton Live                                   │
│  ┌───────────────────────────────────────────┐  │
│  │ ChatM4L.amxd                              │  │
│  │  ┌─────────────┐    ┌──────────────────┐  │  │
│  │  │  bridge.js  │◄──►│  node.script     │  │  │
│  │  │  (v8)       │    │  main.js         │  │  │
│  │  │             │    │  ├── config.js   │  │  │
│  │  │  Live API   │    │  ├── client.js   │  │  │
│  │  │  Track info │    │  ├── sessions.js │  │  │
│  │  │  Devices    │    │  └── commands/   │  │  │
│  │  └─────────────┘    └──────────────────┘  │  │
│  └───────────────────────────────────────────┘  │
│                           │                      │
└───────────────────────────│──────────────────────┘
                            │ HTTP
                            ▼
                    ┌───────────────┐
                    │  AI Provider  │
                    │  (Claude/GPT) │
                    └───────────────┘
```

**bridge.js (v8)**: Runs in Max, accesses Live API, reads track/device info
**main.js (node.script)**: Runs in Node.js, handles AI communication

## Files

| File | Purpose |
|------|---------|
| `bridge.js` | Live API bridge, UI routing |
| `ai/main.js` | Main entry point, message handling |
| `ai/config.js` | Config/prompt/skill management |
| `ai/client.js` | Multi-provider AI client |
| `ai/sessions.js` | Conversation persistence |
| `ai/commands/` | Slash command handlers |
| `ai/defaults/` | Default config/prompts/skills |

## Requirements

- Ableton Live 12.2+ (Max 9 with v8 and node.script)
- Max for Live (included in Suite)
- API key (Anthropic, OpenAI, or local model)

## Development

See [BUILD.md](BUILD.md) for building the device from scratch.

To reload code changes:
- `bridge.js`: Saved automatically (v8 @autowatch)
- `main.js`: Send `script reload` to node.script

## License

MIT
