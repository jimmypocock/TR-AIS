"""
Personality Engine for TR-AIS / Maestro

This module creates a persistent "musical personality" that learns from every interaction.
It tracks:
- Artist profile (who they are, what they make)
- Learned preferences (what they accept/reject)
- Vocabulary mappings (what their words mean musically)
- Musical memory (named patterns, favorites)

The personality context is assembled and injected into every Claude request,
making the AI feel like a bandmate who knows you.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Preference:
    """A learned preference about the artist's taste."""
    feature: str  # e.g., "ghost_notes_snare", "four_on_floor", "busy_hats"
    sentiment: str  # "positive" or "negative"
    strength: float  # 0-1, increases with repetition
    examples: list = field(default_factory=list)  # pattern snippets that led to this
    learned_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class VocabMapping:
    """Maps artist's natural language to musical meaning."""
    term: str  # "punchy", "fat", "driving"
    meaning: str  # "more attack on kick, tighter decay"
    confidence: float  # 0-1
    examples: list = field(default_factory=list)


@dataclass
class MusicalMemory:
    """A saved pattern the artist liked."""
    name: str  # "the Tuesday groove", "Midnight Drive drums"
    pattern: dict
    tags: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""


@dataclass 
class FeedbackEvent:
    """Records artist feedback on a pattern."""
    pattern: dict
    feedback_type: str  # 'accepted', 'rejected', 'loved', 'modified', 'reverted'
    user_comment: Optional[str]
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PersonalityEngine:
    """
    Maintains and evolves the artist's musical personality profile.
    
    Usage:
        personality = PersonalityEngine("./personality.json")
        
        # Get context for Claude
        context = personality.assemble_context(current_pattern, recent_conversation)
        
        # Record feedback
        personality.record_feedback(pattern, "accepted", "this groove is perfect")
        
        # Save a favorite
        personality.save_memory("the good shuffle", pattern, tags=["blues", "favorite"])
    """
    
    def __init__(self, filepath: str = "personality.json"):
        self.filepath = Path(filepath)
        self.data = self._load()
    
    def _load(self) -> dict:
        """Load personality data or create default."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                print(f"🧠 Loaded personality: {len(data.get('preferences', []))} preferences, {len(data.get('memories', []))} memories")
                return data
            except Exception as e:
                print(f"Warning: Could not load personality: {e}")
        
        # Default personality structure
        return {
            "artist_profile": {
                "name": None,
                "bio": None,  # Free-form description, can be Claude-maintained
                "genres": {},  # {"80s_ballad": 0.8, "blues": 0.6}
                "tempo_range": [70, 130],
                "default_swing": 25,
                "instruments": [],  # ["TR-8S", "Moog Sub-37"]
                "created_at": datetime.now().isoformat(),
            },
            "preferences": [],  # List of Preference dicts
            "vocabulary": [],  # List of VocabMapping dicts
            "memories": [],  # List of MusicalMemory dicts
            "feedback_history": [],  # List of FeedbackEvent dicts
            "stats": {
                "sessions_count": 0,
                "patterns_generated": 0,
                "patterns_accepted": 0,
                "patterns_rejected": 0,
            }
        }
    
    def save(self):
        """Persist personality to disk."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save personality: {e}")
    
    # --- Artist Profile ---
    
    def update_profile(self, **kwargs):
        """Update artist profile fields."""
        for key, value in kwargs.items():
            if key in self.data["artist_profile"]:
                self.data["artist_profile"][key] = value
        self.save()
    
    def add_genre(self, genre: str, weight: float = 0.5):
        """Add or update a genre weight."""
        self.data["artist_profile"]["genres"][genre] = max(0, min(1, weight))
        self.save()
    
    # --- Preferences ---
    
    def record_feedback(self, pattern: dict, feedback_type: str, 
                        user_comment: Optional[str] = None,
                        session_id: str = "unknown"):
        """
        Record feedback on a pattern and update preferences.
        
        feedback_type: 'accepted', 'rejected', 'loved', 'modified', 'reverted'
        """
        # Store the event
        event = FeedbackEvent(
            pattern=pattern,
            feedback_type=feedback_type,
            user_comment=user_comment,
            session_id=session_id,
        )
        self.data["feedback_history"].append(asdict(event))
        
        # Update stats
        self.data["stats"]["patterns_generated"] += 1
        if feedback_type in ("accepted", "loved"):
            self.data["stats"]["patterns_accepted"] += 1
        elif feedback_type == "rejected":
            self.data["stats"]["patterns_rejected"] += 1
        
        # Learn from feedback
        if feedback_type == "rejected" and user_comment:
            self._learn_from_rejection(pattern, user_comment)
        elif feedback_type in ("accepted", "loved"):
            self._learn_from_acceptance(pattern, user_comment)
        
        self.save()
    
    def _learn_from_rejection(self, pattern: dict, comment: str):
        """Extract negative preferences from rejection."""
        comment_lower = comment.lower()
        
        # Pattern feature detection
        features_detected = []
        
        # Check what was in the pattern
        instruments = pattern.get("instruments", {})
        
        # Busy hats
        ch_steps = instruments.get("CH", {}).get("steps", [])
        if ch_steps.count(0) < 4:  # More than 12 hits = busy
            if any(word in comment_lower for word in ["busy", "too much", "simpler", "less"]):
                features_detected.append("busy_hats")
        
        # Four on floor
        bd_steps = instruments.get("BD", {}).get("steps", [])
        if bd_steps[0:16:4] == [bd_steps[0]] * 4 and bd_steps[0] > 0:  # Kick on every beat
            if any(word in comment_lower for word in ["techno", "four", "floor", "straight"]):
                features_detected.append("four_on_floor")
        
        # Ghost notes
        sd_steps = instruments.get("SD", {}).get("steps", [])
        if any(0 < v < 70 for v in sd_steps):  # Has ghost notes
            if any(word in comment_lower for word in ["ghost", "subtle", "quiet"]):
                features_detected.append("ghost_notes_snare")
        
        # Generic "too much" detection
        if any(word in comment_lower for word in ["too much", "busy", "cluttered", "overloaded"]):
            features_detected.append("complexity_high")
        
        # Add or strengthen negative preferences
        for feature in features_detected:
            self._update_preference(feature, "negative", pattern)
    
    def _learn_from_acceptance(self, pattern: dict, comment: Optional[str]):
        """Extract positive preferences from acceptance."""
        instruments = pattern.get("instruments", {})
        features_detected = []
        
        # Detect features present in accepted patterns
        
        # Swing
        swing = pattern.get("swing", 0)
        if swing > 20:
            features_detected.append(f"swing_{swing // 20 * 20}")  # swing_20, swing_40, etc.
        
        # Ghost notes on snare (if present and accepted)
        sd_steps = instruments.get("SD", {}).get("steps", [])
        if any(0 < v < 70 for v in sd_steps):
            features_detected.append("ghost_notes_snare")
        
        # Open hat on upbeats
        oh_steps = instruments.get("OH", {}).get("steps", [])
        if oh_steps and any(oh_steps[i] > 0 for i in [2, 6, 10, 14]):  # Upbeats
            features_detected.append("open_hat_upbeats")
        
        # Rim shot presence
        if instruments.get("RS", {}).get("steps", []):
            features_detected.append("rim_shot_use")
        
        # Add or strengthen positive preferences
        for feature in features_detected:
            self._update_preference(feature, "positive", pattern)
    
    def _update_preference(self, feature: str, sentiment: str, pattern: dict):
        """Add or strengthen a preference."""
        existing = next(
            (p for p in self.data["preferences"] 
             if p["feature"] == feature and p["sentiment"] == sentiment),
            None
        )
        
        if existing:
            # Strengthen existing preference
            existing["strength"] = min(1.0, existing["strength"] + 0.15)
            existing["examples"].append({
                "bpm": pattern.get("bpm"),
                "swing": pattern.get("swing"),
                "instruments": list(pattern.get("instruments", {}).keys()),
            })
            # Keep only last 5 examples
            existing["examples"] = existing["examples"][-5:]
        else:
            # Create new preference
            pref = Preference(
                feature=feature,
                sentiment=sentiment,
                strength=0.3,
                examples=[{
                    "bpm": pattern.get("bpm"),
                    "swing": pattern.get("swing"),
                    "instruments": list(pattern.get("instruments", {}).keys()),
                }]
            )
            self.data["preferences"].append(asdict(pref))
    
    def get_preferences_summary(self) -> str:
        """Format preferences for Claude context."""
        if not self.data["preferences"]:
            return "No learned preferences yet."
        
        positives = [p for p in self.data["preferences"] if p["sentiment"] == "positive" and p["strength"] > 0.3]
        negatives = [p for p in self.data["preferences"] if p["sentiment"] == "negative" and p["strength"] > 0.3]
        
        lines = []
        
        if positives:
            lines.append("LIKES:")
            for p in sorted(positives, key=lambda x: -x["strength"]):
                feature_readable = p["feature"].replace("_", " ")
                lines.append(f"  ✓ {feature_readable} (strength: {p['strength']:.0%})")
        
        if negatives:
            lines.append("DISLIKES:")
            for p in sorted(negatives, key=lambda x: -x["strength"]):
                feature_readable = p["feature"].replace("_", " ")
                lines.append(f"  ✗ {feature_readable} (strength: {p['strength']:.0%})")
        
        return "\n".join(lines) if lines else "Still learning preferences..."
    
    # --- Vocabulary ---
    
    def learn_vocabulary(self, term: str, meaning: str, example_delta: dict = None):
        """Learn what a term means to this artist."""
        existing = next((v for v in self.data["vocabulary"] if v["term"].lower() == term.lower()), None)
        
        if existing:
            existing["confidence"] = min(1.0, existing["confidence"] + 0.2)
            if example_delta:
                existing["examples"].append(example_delta)
                existing["examples"] = existing["examples"][-5:]
        else:
            vocab = VocabMapping(
                term=term,
                meaning=meaning,
                confidence=0.5,
                examples=[example_delta] if example_delta else []
            )
            self.data["vocabulary"].append(asdict(vocab))
        
        self.save()
    
    def get_vocabulary_summary(self) -> str:
        """Format vocabulary for Claude context."""
        if not self.data["vocabulary"]:
            return ""
        
        high_confidence = [v for v in self.data["vocabulary"] if v["confidence"] > 0.4]
        if not high_confidence:
            return ""
        
        lines = ["VOCABULARY (what this artist means when they say...):"]
        for v in sorted(high_confidence, key=lambda x: -x["confidence"]):
            lines.append(f'  "{v["term"]}" → {v["meaning"]}')
        
        return "\n".join(lines)
    
    # --- Musical Memory ---
    
    def save_memory(self, name: str, pattern: dict, tags: list = None, notes: str = ""):
        """Save a pattern to memory with a name."""
        memory = MusicalMemory(
            name=name,
            pattern=pattern,
            tags=tags or [],
            notes=notes
        )
        
        # Remove existing memory with same name
        self.data["memories"] = [m for m in self.data["memories"] if m["name"].lower() != name.lower()]
        
        self.data["memories"].append(asdict(memory))
        self.save()
        return memory
    
    def recall_memory(self, query: str) -> Optional[dict]:
        """Find a saved pattern by name or tag."""
        query_lower = query.lower()
        
        # Exact name match
        for m in self.data["memories"]:
            if m["name"].lower() == query_lower:
                return m
        
        # Partial name match
        for m in self.data["memories"]:
            if query_lower in m["name"].lower():
                return m
        
        # Tag match
        for m in self.data["memories"]:
            if any(query_lower in tag.lower() for tag in m.get("tags", [])):
                return m
        
        return None
    
    def get_memories_summary(self) -> str:
        """Format memories for Claude context."""
        if not self.data["memories"]:
            return ""
        
        lines = ["SAVED PATTERNS:"]
        for m in self.data["memories"][-10:]:  # Last 10
            tags_str = f" [{', '.join(m['tags'])}]" if m.get("tags") else ""
            lines.append(f'  - "{m["name"]}"{tags_str}')
        
        return "\n".join(lines)
    
    # --- Context Assembly ---
    
    def assemble_context(self, current_pattern: dict = None) -> str:
        """
        Build the complete personality context to inject into Claude's prompt.
        This is the key method that makes Claude feel like it knows you.
        """
        sections = []
        
        # Artist profile
        profile = self.data["artist_profile"]
        if profile.get("bio") or profile.get("genres"):
            profile_lines = ["## About This Artist"]
            if profile.get("name"):
                profile_lines.append(f"Name: {profile['name']}")
            if profile.get("bio"):
                profile_lines.append(profile["bio"])
            if profile.get("genres"):
                genres_str = ", ".join(f"{g} ({w:.0%})" for g, w in 
                                       sorted(profile["genres"].items(), key=lambda x: -x[1]))
                profile_lines.append(f"Genre tendencies: {genres_str}")
            if profile.get("tempo_range"):
                profile_lines.append(f"Preferred tempo: {profile['tempo_range'][0]}-{profile['tempo_range'][1]} BPM")
            if profile.get("instruments"):
                profile_lines.append(f"Instruments: {', '.join(profile['instruments'])}")
            sections.append("\n".join(profile_lines))
        
        # Preferences
        prefs = self.get_preferences_summary()
        if prefs and prefs != "No learned preferences yet.":
            sections.append(f"## Learned Preferences\n{prefs}")
        
        # Vocabulary
        vocab = self.get_vocabulary_summary()
        if vocab:
            sections.append(f"## {vocab}")
        
        # Memories
        memories = self.get_memories_summary()
        if memories:
            sections.append(f"## {memories}")
        
        # Stats
        stats = self.data["stats"]
        if stats["patterns_generated"] > 0:
            acceptance_rate = stats["patterns_accepted"] / stats["patterns_generated"] if stats["patterns_generated"] > 0 else 0
            sections.append(f"## Working History\nSessions: {stats['sessions_count']}, Patterns created: {stats['patterns_generated']}, Acceptance rate: {acceptance_rate:.0%}")
        
        if sections:
            return "\n\n".join(sections)
        else:
            return "This is a new artist. Learn their style as you work together."
    
    # --- Session Tracking ---
    
    def start_session(self):
        """Call at start of a new session."""
        self.data["stats"]["sessions_count"] += 1
        self.save()
    
    # --- Commands ---
    
    def handle_command(self, text: str, current_pattern: dict = None) -> Optional[str]:
        """
        Check if user message is a personality command.
        Returns response string if handled, None if not a command.
        """
        text_lower = text.lower().strip()
        
        # Save pattern command
        save_match = re.match(r"(?:save|remember)\s+(?:this\s+)?(?:as\s+)?[\"']?(.+?)[\"']?\s*$", text_lower)
        if save_match and current_pattern:
            name = save_match.group(1)
            self.save_memory(name, current_pattern)
            return f"💾 Saved as \"{name}\""
        
        # Recall pattern command
        recall_match = re.match(r"(?:recall|play|load|get)\s+[\"']?(.+?)[\"']?\s*$", text_lower)
        if recall_match:
            name = recall_match.group(1)
            memory = self.recall_memory(name)
            if memory:
                return {"recall": memory}  # Signal to load this pattern
            return f"🤔 I don't have a pattern called \"{name}\""
        
        # "I hate X" / "I don't like X"
        hate_match = re.match(r"i\s+(?:hate|don'?t\s+like|dislike)\s+(.+)", text_lower)
        if hate_match:
            feature = hate_match.group(1).strip()
            self._update_preference(feature.replace(" ", "_"), "negative", current_pattern or {})
            self.save()
            return f"📝 Noted — I'll avoid {feature}"
        
        # "I love X" / "I like X"
        love_match = re.match(r"i\s+(?:love|like|want\s+more)\s+(.+)", text_lower)
        if love_match:
            feature = love_match.group(1).strip()
            self._update_preference(feature.replace(" ", "_"), "positive", current_pattern or {})
            self.save()
            return f"📝 Noted — I'll use more {feature}"
        
        # Profile updates
        if text_lower.startswith("my name is "):
            name = text[11:].strip()
            self.update_profile(name=name)
            return f"👋 Nice to meet you, {name}!"
        
        if text_lower.startswith("i make ") or text_lower.startswith("i produce "):
            genre = text.split(" ", 2)[-1].strip()
            self.add_genre(genre, 0.7)
            return f"🎵 Cool, I'll keep {genre} in mind"
        
        return None