# TR-AIS Personality Layer — Integration Guide

This document explains the personality system addition to TR-AIS. Use this to understand the vision and port the changes to the existing codebase.

## Vision

The personality layer transforms TR-AIS from a "drum pattern generator" into a **musical collaborator that learns**. Like a session drummer who works with an artist for years, the system builds up knowledge of:

- **Who the artist is** (genres, instruments, style)
- **What they like** (accepted patterns, positive feedback)
- **What they hate** (rejected patterns, negative feedback)
- **What their words mean** ("punchy" → more attack, "fat" → layer + sub)
- **Patterns they loved** (saveable/recallable by name)

This context is assembled and injected into every Claude request, making the AI feel like a bandmate who knows you.

## New Files

### `personality_engine.py` (NEW)

The core personality system. Handles:

- Artist profile storage (name, bio, genres, tempo preferences)
- Preference learning (tracks accepts/rejects, extracts features)
- Vocabulary mapping (learns what artist's words mean)
- Musical memory (save/recall named patterns)
- Feedback recording and analysis
- Context assembly (builds the personality prompt for Claude)

Key classes:

- `PersonalityEngine` — main class, instantiate once at startup
- `Preference` — a learned like/dislike
- `VocabMapping` — term → meaning mapping
- `MusicalMemory` — saved pattern with name/tags

Key methods:

```python
personality = PersonalityEngine("personality.json")

# Get context for Claude (call this when building the prompt)
context = personality.assemble_context(current_pattern)

# Record feedback on a pattern
personality.record_feedback(pattern, "accepted", "this groove is perfect", session_id)

# Save a pattern to memory
personality.save_memory("the good shuffle", pattern, tags=["blues", "favorite"])

# Recall a pattern
memory = personality.recall_memory("good shuffle")  # Returns pattern dict

# Handle commands like "save this as X" or "I hate four-on-floor"
result = personality.handle_command(user_text, current_pattern)
```

### `pattern_generator.py` (MODIFIED)

Changes:

- Constructor now accepts optional `personality: PersonalityEngine`
- `generate()` method builds system prompt with personality context
- Added `BASE_SYSTEM_PROMPT` constant (same content, just renamed)

Key change in `generate()`:

```python
system_prompt = BASE_SYSTEM_PROMPT

if self.personality:
    personality_context = self.personality.assemble_context(current_pattern)
    if personality_context:
        system_prompt += f"\n\n---\n\n# WHAT YOU KNOW ABOUT THIS ARTIST\n\n{personality_context}"
```

### `main.py` (MODIFIED)

Changes:

- Imports `PersonalityEngine`
- Creates `personality` global at startup
- Passes personality to `PatternGenerator`
- Calls `personality.start_session()` on startup
- Checks for personality commands before sending to Claude
- New endpoint: `POST /api/sessions/{id}/feedback` — record accept/reject
- New endpoint: `GET /api/personality` — view personality state
- New endpoint: `GET /api/personality/context` — see what Claude sees
- New endpoint: `POST /api/personality/profile` — update artist profile

The message flow now:

1. User sends message
2. Check if it's a personality command (save as, recall, I hate X)
3. If command → handle directly, return
4. If not → build Claude messages with current pattern context
5. Call `generator.generate()` (which injects personality)
6. Store conversation and pattern
7. Return to user

## Feedback Flow

To teach the system what the artist likes:

```
POST /api/sessions/{session_id}/feedback
{
  "feedback_type": "accepted" | "rejected" | "loved",
  "comment": "optional comment like 'too busy'"
}
```

The `personality_engine` analyzes the pattern + comment to extract features:

- If pattern had busy hats and user said "too much" → learns "busy_hats" = negative
- If pattern had ghost notes and was accepted → learns "ghost_notes_snare" = positive

Over time, this builds a preference profile that influences Claude's output.

## Command Handling

The personality engine handles these natural language commands:

| Command | Example | Effect |
|---------|---------|--------|
| Save pattern | "save this as the good shuffle" | Stores pattern to memory |
| Recall pattern | "play the good shuffle" | Loads pattern from memory |
| Express dislike | "I hate four-on-floor" | Adds negative preference |
| Express like | "I love ghost notes" | Adds positive preference |
| Set name | "my name is Jimmy" | Updates profile |
| Set genre | "I make 80s ballads" | Adds genre weight |

Commands are checked BEFORE sending to Claude, so they're fast and don't waste API calls.

## Context Assembly

When Claude receives a request, the system prompt includes something like:

```
## About This Artist
Name: Jimmy
Producer who gravitates toward 80s ballads, blues, and pop. Values groove over complexity.
Genre tendencies: 80s_ballad (80%), pop (70%), blues (60%)
Preferred tempo: 70-130 BPM
Instruments: TR-8S, Moog Sub-37

## Learned Preferences
LIKES:
  ✓ ghost notes snare (strength: 60%)
  ✓ open hat upbeats (strength: 45%)
  ✓ swing 40 (strength: 75%)

DISLIKES:
  ✗ busy hats (strength: 80%)
  ✗ four on floor (strength: 90%)

## VOCABULARY (what this artist means when they say...)
  "punchy" → more attack on kick, tighter decay
  "fat" → layer sounds, boost sub frequencies
  "driving" → steady 8ths, strong downbeats, NOT faster tempo

## SAVED PATTERNS:
  - "the Tuesday groove" [blues, favorite]
  - "Midnight Drive drums" [ballad]

## Working History
Sessions: 12, Patterns created: 47, Acceptance rate: 72%
```

This context makes Claude's responses personalized and consistent with learned preferences.

## Data Persistence

- `personality.json` — all personality data (auto-saved on changes)
- `sessions.json` — session data (unchanged from before)

The personality file structure:

```json
{
  "artist_profile": {
    "name": "Jimmy",
    "bio": "...",
    "genres": {"80s_ballad": 0.8},
    "tempo_range": [70, 130],
    "instruments": ["TR-8S"]
  },
  "preferences": [...],
  "vocabulary": [...],
  "memories": [...],
  "feedback_history": [...],
  "stats": {
    "sessions_count": 12,
    "patterns_generated": 47,
    "patterns_accepted": 34,
    "patterns_rejected": 8
  }
}
```

## UI Changes Needed

The current UI works without changes, but to fully leverage the personality system, consider adding:

1. **Feedback buttons** — thumbs up/down on each pattern version
2. **Save button** — quick save current pattern with name prompt
3. **Memories panel** — show saved patterns, click to recall
4. **Personality indicator** — show that the system is "learning"

Minimal approach: Just add 👍/👎 buttons that call the feedback endpoint.

## Integration Steps for Claude Code

1. Copy `personality_engine.py` to project root
2. Replace `pattern_generator.py` with new version
3. Replace `main.py` with new version (or merge changes)
4. Test: Run server, create session, send message — check that personality context appears in Claude prompt (use `/api/personality/context` endpoint)
5. Add feedback UI elements as desired

## Future Enhancements

- **Vocabulary learning from conversation** — detect when user explains a term
- **Pattern similarity matching** — "something like the Tuesday groove but faster"
- **Project-scoped preferences** — different styles for different projects
- **Export/import personality** — share or backup personality data
- **Multi-artist support** — switch between artist profiles
