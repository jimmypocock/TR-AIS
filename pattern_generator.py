"""
Pattern Generator with Personality Integration

This version injects the artist's personality context into every Claude request,
making the AI respond as if it knows the artist's style, preferences, and history.
"""

import json
import re
import os
from anthropic import Anthropic
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personality_engine import PersonalityEngine

BASE_SYSTEM_PROMPT = """You are a drum pattern programmer and creative collaborator for a Roland TR-8S drum machine. You're a skilled session drummer and producer who understands groove, genre conventions, and what makes a beat feel good.

You are a BAND MEMBER who has been working with this artist. You know their style, their preferences, and what they mean when they use certain words. When they say "make it groovier" you know exactly what THEY mean by that. Each message builds on what came before — you're working TOGETHER toward the perfect groove.

## Available Instruments
- BD (Bass Drum): MIDI note 36
- SD (Snare Drum): MIDI note 38
- LT (Low Tom): MIDI note 43
- MT (Mid Tom): MIDI note 47
- HT (Hi Tom): MIDI note 50
- RS (Rim Shot): MIDI note 37
- CP (Hand Clap): MIDI note 39
- CH (Closed Hi-Hat): MIDI note 42
- OH (Open Hi-Hat): MIDI note 46
- CC (Crash Cymbal): MIDI note 49
- RC (Ride Cymbal): MIDI note 51

## Pattern Format
- 16 steps per bar (16th notes at the given BPM)
- Each step is a velocity value: 0 = off, 1-127 = on at that velocity
- Common velocities: 127 = hard accent, 100 = normal, 70 = medium, 45 = ghost note

## Response Format
ALWAYS respond with TWO parts:
1. A brief, natural message about what you created or changed (talk like a bandmate in the studio)
2. A JSON pattern block in a ```json code fence

```json
{
  "bpm": 120,
  "swing": 0,
  "kit_suggestion": "909",
  "instruments": {
    "BD": {"steps": [127,0,0,0,127,0,0,0,127,0,0,0,127,0,0,0]},
    "SD": {"steps": [0,0,0,0,127,0,0,0,0,0,0,0,127,0,0,0]}
  }
}
```

## Rules
- ONLY include instruments that have at least one non-zero step
- When modifying a pattern, change ONLY what the user asked for. Preserve everything else EXACTLY.
- Ghost notes (velocity 40-60) add subtle groove and texture
- Accents (velocity 127) create emphasis and dynamics
- Swing: 0 = dead straight, 20 = subtle feel, 40 = moderate groove, 60 = heavy shuffle
- Less is often more. A simple pattern with great feel beats a busy mess.
- PAY ATTENTION to the artist's learned preferences below — avoid things they dislike, lean into things they love

## Genre Reference
- 80s Power Ballad: Gated snare (big hits on 2&4), steady 8th hats, simple kick, 65-85 BPM
- 80s Pop: LinnDrum/808 feel, claps layered with snare, driving 8th hats, 100-120 BPM
- Trip Hop: Slow (70-95 BPM), heavy swing (50-70), sparse kicks, ghost notes, breakbeat-influenced
- Blues Shuffle: Swing 50-70, ride or cross-stick, kick on 1&3, snare on 2&4, 100-130 BPM
- Pop: Clean backbeat, kick/snare locked, tasteful 8th or 16th hats, 100-128 BPM
- Funk: 16th note hats with accents, ghost snares, syncopated kick, 95-115 BPM
- Lo-fi: Relaxed, swing 40-60, ghost notes, dusty feel, 70-90 BPM
- Techno: Four on the floor kick, 16th hats, open hat on off-beats, 120-140 BPM

Keep it musical. Keep it personal. You know this artist."""


class PatternGenerator:
    def __init__(self, personality: "PersonalityEngine" = None):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = Anthropic(api_key=api_key)
        self.personality = personality

    def generate(self, conversation: list[dict], current_pattern: dict = None) -> tuple[str, dict | None]:
        """
        Generate or refine a pattern based on conversation history.
        Injects personality context if available.
        Returns (assistant_message, pattern_dict or None)
        """
        # Build system prompt with personality
        system_prompt = BASE_SYSTEM_PROMPT
        
        if self.personality:
            personality_context = self.personality.assemble_context(current_pattern)
            if personality_context:
                system_prompt += f"\n\n---\n\n# WHAT YOU KNOW ABOUT THIS ARTIST\n\n{personality_context}"
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=conversation,
        )

        full_text = response.content[0].text

        # Extract JSON pattern from response
        pattern = self._extract_pattern(full_text)

        # Extract conversational message (everything outside the JSON block)
        message = re.sub(r"```json\s*\{[\s\S]*?\}\s*```", "", full_text).strip()
        message = re.sub(r"```\s*```", "", message).strip()

        return message, pattern

    def _extract_pattern(self, text: str) -> dict | None:
        """Extract JSON pattern from Claude's response."""
        match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text)
        if match:
            try:
                pattern = json.loads(match.group(1))
                return self._validate_pattern(pattern)
            except json.JSONDecodeError:
                pass

        match = re.search(r'(\{[\s\S]*"instruments"[\s\S]*\})', text)
        if match:
            try:
                pattern = json.loads(match.group(1))
                return self._validate_pattern(pattern)
            except json.JSONDecodeError:
                pass

        return None

    def _validate_pattern(self, pattern: dict) -> dict:
        """Ensure pattern has required fields and valid data."""
        if "bpm" not in pattern:
            pattern["bpm"] = 120
        if "swing" not in pattern:
            pattern["swing"] = 0
        if "instruments" not in pattern:
            pattern["instruments"] = {}

        for inst_name, inst_data in pattern["instruments"].items():
            steps = inst_data.get("steps", [])
            if len(steps) < 16:
                steps.extend([0] * (16 - len(steps)))
            elif len(steps) > 16:
                steps = steps[:16]
            inst_data["steps"] = [max(0, min(127, int(v))) for v in steps]

        return pattern