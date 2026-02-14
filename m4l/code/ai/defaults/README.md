# ChatM4L Configuration

This folder contains your ChatM4L configuration.

## Quick Start

1. Edit `config.json` with your API key
2. Run `/reload` in the chat to apply changes
3. Start chatting!

## Files

- **config.json** - API keys, provider settings, model selection
- **core/system.md** - AI personality and instructions
- **core/user.md** - Your musical profile (edit this!)
- **skills/*.md** - Specialized skill prompts

## Commands

| Command | Description |
|---------|-------------|
| `/reload` | Reload config after editing |
| `/resetconfig` | Reset to defaults (backs up current) |
| `/openconfig` | Show this folder path |
| `/skills` | List available skills |
| `/help` | Show all commands |

## Adding Skills

Create a `.md` file in `skills/`:

```
skills/
└── my-skill.md
```

The skill will auto-discover. Activate with `/my-skill`.

## Providers

### Anthropic (default)
```json
"anthropic": {
  "apiKey": "sk-ant-...",
  "models": { "default": "claude-sonnet-4-20250514" }
}
```

### OpenAI
```json
"openai": {
  "apiKey": "sk-...",
  "models": { "default": "gpt-4o" }
}
```

### Local Models (Ollama/LM Studio)
```json
"ollama": {
  "apiKey": null,
  "baseUrl": "http://localhost:11434/v1",
  "models": { "default": "llama3" }
}
```

Set `"activeProvider": "ollama"` to use.
