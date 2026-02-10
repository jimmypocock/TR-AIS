"""
Claude Engine for Ableton AI Assistant.

Takes natural language input + session state, returns structured Ableton commands.
"""

import json
from dataclasses import dataclass, field
from typing import Optional
import anthropic

from .config import config


# Available actions that can be returned
AVAILABLE_ACTIONS = {
    # Transport
    "play": {"params": []},
    "stop": {"params": []},
    "set_tempo": {"params": ["bpm"]},
    "toggle_metronome": {"params": []},

    # Tracks
    "create_midi_track": {"params": ["name"]},
    "create_audio_track": {"params": ["name"]},
    "delete_track": {"params": ["track_index"]},
    "set_track_volume": {"params": ["track_index", "volume"]},
    "set_track_pan": {"params": ["track_index", "pan"]},
    "set_track_mute": {"params": ["track_index", "muted"]},
    "set_track_solo": {"params": ["track_index", "soloed"]},
    "set_track_arm": {"params": ["track_index", "armed"]},

    # Devices
    "set_device_parameter": {"params": ["track_index", "device_index", "param_index", "value"]},
}


SYSTEM_PROMPT = """You are an AI assistant that controls Ableton Live. You translate natural language requests into specific Ableton commands.

## Your Role
- Understand what the user wants to do in their Ableton session
- Return structured commands that will be executed in Ableton
- Be conversational in your response to the user

## Available Actions

### Transport
- play: Start playback
- stop: Stop playback
- set_tempo: Set BPM (params: bpm as float, e.g., 120.0)
- toggle_metronome: Toggle metronome on/off

### Tracks
- create_midi_track: Create a new MIDI track (params: name as string)
- create_audio_track: Create a new audio track (params: name as string)
- delete_track: Delete a track (params: track_index as int, 0-based)
- set_track_volume: Set track volume (params: track_index as int, volume as float 0.0-1.0)
- set_track_pan: Set track pan (params: track_index as int, pan as float -1.0 to 1.0)
- set_track_mute: Mute/unmute track (params: track_index as int, muted as bool)
- set_track_solo: Solo/unsolo track (params: track_index as int, soloed as bool)
- set_track_arm: Arm/disarm track for recording (params: track_index as int, armed as bool)

### Devices
- set_device_parameter: Set a device parameter (params: track_index, device_index, param_index, value as float 0.0-1.0)

## Session State
You will receive the current session state including:
- Current tempo
- Whether playback is running
- List of tracks with their names, types, volumes, etc.

Use this information to understand the user's context. For example, if they say "make the drums louder", find the track named "Drums" and adjust its volume.

## Response Format
You MUST respond with valid JSON in this exact format:
{
    "thinking": "Brief explanation of what you understood and your plan",
    "commands": [
        {"action": "action_name", "params": {"param1": value1, "param2": value2}}
    ],
    "response": "Conversational response to the user about what you did"
}

## Examples

User: "create a synth track and set tempo to 95"
Response:
{
    "thinking": "User wants a new MIDI track for synth and to change the tempo to 95 BPM",
    "commands": [
        {"action": "create_midi_track", "params": {"name": "Synth"}},
        {"action": "set_tempo", "params": {"bpm": 95.0}}
    ],
    "response": "Created a new synth track and set the tempo to 95 BPM."
}

User: "make track 2 quieter" (with session state showing track 1 is at volume 0.8)
Response:
{
    "thinking": "User wants to reduce volume on track index 1 (track 2 in human terms). Current volume is 0.8, I'll reduce it.",
    "commands": [
        {"action": "set_track_volume", "params": {"track_index": 1, "volume": 0.5}}
    ],
    "response": "Lowered the volume on track 2."
}

User: "mute the drums" (with session state showing "Drums" is track index 0)
Response:
{
    "thinking": "User wants to mute the track named 'Drums' which is at index 0",
    "commands": [
        {"action": "set_track_mute", "params": {"track_index": 0, "muted": true}}
    ],
    "response": "Muted the Drums track."
}

## Important Notes
- Track indices are 0-based (track 1 = index 0, track 2 = index 1, etc.)
- When the user says "track N", they usually mean the Nth track (1-based), so convert to 0-based index
- Volume ranges from 0.0 (silent) to 1.0 (full)
- Pan ranges from -1.0 (full left) to 1.0 (full right), 0.0 is center
- If a request is ambiguous, make a reasonable assumption and explain it in your response
- If you can't fulfill a request, return empty commands array and explain why in response
"""


@dataclass
class ClaudeResponse:
    """Structured response from Claude."""
    thinking: str = ""
    commands: list = field(default_factory=list)
    response: str = ""
    error: Optional[str] = None


class ClaudeEngine:
    """Engine for processing natural language into Ableton commands."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize the Claude engine.

        Args:
            api_key: Anthropic API key. If not provided, uses config.
            model: Model to use. If not provided, uses config.
        """
        self.api_key = api_key or config.anthropic_api_key
        self.model = model or config.claude_model
        self.max_tokens = config.claude_max_tokens

        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def process(self, message: str, session_state: dict = None) -> ClaudeResponse:
        """Process a natural language message and return Ableton commands.

        Args:
            message: User's natural language request
            session_state: Current Ableton session state (tempo, tracks, etc.)

        Returns:
            ClaudeResponse with thinking, commands, and response
        """
        session_state = session_state or {}

        # Build the user message with session context
        user_content = self._build_user_message(message, session_state)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_content}
                ]
            )

            # Parse the response
            return self._parse_response(response.content[0].text)

        except anthropic.APIError as e:
            return ClaudeResponse(error=f"API error: {str(e)}")
        except Exception as e:
            return ClaudeResponse(error=f"Error: {str(e)}")

    def _build_user_message(self, message: str, session_state: dict) -> str:
        """Build the user message with session context."""
        parts = []

        if session_state:
            parts.append("## Current Session State")
            parts.append(f"```json\n{json.dumps(session_state, indent=2)}\n```")
            parts.append("")

        parts.append("## User Request")
        parts.append(message)

        return "\n".join(parts)

    def _parse_response(self, text: str) -> ClaudeResponse:
        """Parse Claude's response into structured format."""
        try:
            # Try to extract JSON from the response
            # Claude might wrap it in markdown code blocks
            json_text = text

            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                json_text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                json_text = text[start:end].strip()

            data = json.loads(json_text)

            return ClaudeResponse(
                thinking=data.get("thinking", ""),
                commands=data.get("commands", []),
                response=data.get("response", "")
            )

        except json.JSONDecodeError as e:
            return ClaudeResponse(
                error=f"Failed to parse response: {str(e)}",
                response=text  # Include raw text for debugging
            )

    def validate_commands(self, commands: list) -> tuple[list, list]:
        """Validate commands against available actions.

        Args:
            commands: List of command dicts

        Returns:
            Tuple of (valid_commands, errors)
        """
        valid = []
        errors = []

        for cmd in commands:
            action = cmd.get("action")
            params = cmd.get("params", {})

            if action not in AVAILABLE_ACTIONS:
                errors.append(f"Unknown action: {action}")
                continue

            # Check required params
            action_info = AVAILABLE_ACTIONS[action]
            missing = [p for p in action_info["params"] if p not in params]

            if missing:
                errors.append(f"Action '{action}' missing params: {missing}")
                continue

            valid.append(cmd)

        return valid, errors
