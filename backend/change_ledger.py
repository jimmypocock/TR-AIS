"""
Change Ledger for Ableton AI Assistant.

Records all changes made to Ableton for undo/redo functionality.
Like git for your session changes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum
import uuid


class ChangeType(Enum):
    """Types of changes we can track."""
    # Transport
    TEMPO = "tempo"
    PLAY_STATE = "play_state"
    METRONOME = "metronome"

    # Track properties
    TRACK_VOLUME = "track_volume"
    TRACK_PAN = "track_pan"
    TRACK_MUTE = "track_mute"
    TRACK_SOLO = "track_solo"
    TRACK_ARM = "track_arm"
    TRACK_NAME = "track_name"

    # Track structure
    TRACK_CREATE = "track_create"
    TRACK_DELETE = "track_delete"

    # Device parameters
    DEVICE_PARAMETER = "device_parameter"


def _parse_track_num(target: str) -> int:
    """Extract 1-indexed track number from target string like 'track:3'."""
    return int(target.split(":")[1]) + 1


def _parse_device_target(target: str) -> tuple[int, int, int]:
    """Extract 1-indexed (track, device, param) from target like 'track:0:device:1:param:2'."""
    parts = target.split(":")
    return (
        int(parts[1]) + 1,  # track
        int(parts[3]) + 1,  # device
        int(parts[5]) + 1,  # param
    )


def _pct(value: float) -> int:
    """Convert 0-1 float to percentage int."""
    return int(float(value) * 100)


@dataclass
class Change:
    """A single recorded change."""
    id: str
    timestamp: datetime
    change_type: ChangeType
    target: str  # e.g., "track:4", "track:2:device:1:param:3", "transport"
    old_value: Any
    new_value: Any
    description: str  # Human-readable: "Set track 5 volume from 85% to 50%"
    reverted: bool = False
    revert_id: Optional[str] = None  # ID of the change that reverted this one

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "change_type": self.change_type.value,
            "target": self.target,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "description": self.description,
            "reverted": self.reverted,
            "revert_id": self.revert_id,
        }


# Description generators for each change type
_DESCRIPTION_GENERATORS = {
    ChangeType.TEMPO: lambda t, o, n: f"Changed tempo from {o} to {n} BPM",
    ChangeType.TRACK_VOLUME: lambda t, o, n: f"Set track {_parse_track_num(t)} volume from {_pct(o)}% to {_pct(n)}%",
    ChangeType.TRACK_PAN: lambda t, o, n: f"Set track {_parse_track_num(t)} pan from {o} to {n}",
    ChangeType.TRACK_MUTE: lambda t, o, n: f"{'Muted' if n else 'Unmuted'} track {_parse_track_num(t)}",
    ChangeType.TRACK_SOLO: lambda t, o, n: f"{'Soloed' if n else 'Unsoloed'} track {_parse_track_num(t)}",
    ChangeType.TRACK_ARM: lambda t, o, n: f"{'Armed' if n else 'Disarmed'} track {_parse_track_num(t)}",
    ChangeType.TRACK_CREATE: lambda t, o, n: f"Created track '{n}'",
    ChangeType.TRACK_DELETE: lambda t, o, n: f"Deleted track {_parse_track_num(t)}",
    ChangeType.DEVICE_PARAMETER: lambda t, o, n: (
        f"Set device parameter (track {_parse_device_target(t)[0]}, "
        f"device {_parse_device_target(t)[1]}, param {_parse_device_target(t)[2]})"
    ),
}


@dataclass
class ChangeLedger:
    """
    Tracks all changes made to Ableton for undo/redo.

    Usage:
        ledger = ChangeLedger()

        # Record a change
        change = ledger.record(
            change_type=ChangeType.TRACK_VOLUME,
            target="track:4",
            old_value=0.85,
            new_value=0.5,
        )

        # Undo last change
        to_undo = ledger.get_undo_candidate()
        # ... execute the undo ...
        ledger.mark_reverted(to_undo.id)

        # Undo last N changes
        to_undo = ledger.get_undo_candidates(n=3)
    """

    changes: list[Change] = field(default_factory=list)
    max_history: int = 100

    def record(
        self,
        change_type: ChangeType,
        target: str,
        old_value: Any,
        new_value: Any,
        description: str = ""
    ) -> Change:
        """Record a new change."""
        change = Change(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            change_type=change_type,
            target=target,
            old_value=old_value,
            new_value=new_value,
            description=description or self._auto_description(change_type, target, old_value, new_value),
        )

        self.changes.append(change)

        if len(self.changes) > self.max_history:
            self.changes = self.changes[-self.max_history:]

        return change

    def _auto_description(
        self,
        change_type: ChangeType,
        target: str,
        old_value: Any,
        new_value: Any
    ) -> str:
        """Generate automatic description for a change."""
        generator = _DESCRIPTION_GENERATORS.get(change_type)
        if generator:
            return generator(target, old_value, new_value)
        return f"Changed {change_type.value}: {old_value} → {new_value}"

    def get_undo_candidate(self) -> Optional[Change]:
        """Get the most recent undoable change."""
        for change in reversed(self.changes):
            if not change.reverted:
                return change
        return None

    def get_undo_candidates(self, n: int = 1) -> list[Change]:
        """Get the N most recent undoable changes (most recent first)."""
        candidates = []
        for change in reversed(self.changes):
            if not change.reverted:
                candidates.append(change)
                if len(candidates) >= n:
                    break
        return candidates

    def mark_reverted(self, change_id: str, revert_id: str = None) -> bool:
        """Mark a change as reverted. Returns True if found."""
        for change in self.changes:
            if change.id == change_id:
                change.reverted = True
                change.revert_id = revert_id
                return True
        return False

    def get_change(self, change_id: str) -> Optional[Change]:
        """Get a change by ID."""
        for change in self.changes:
            if change.id == change_id:
                return change
        return None

    def get_history(self, limit: int = 10, include_reverted: bool = False) -> list[Change]:
        """Get recent change history (most recent first)."""
        result = []
        for change in reversed(self.changes):
            if include_reverted or not change.reverted:
                result.append(change)
                if len(result) >= limit:
                    break
        return result

    def clear(self):
        """Clear all history."""
        self.changes = []

    @property
    def pending_count(self) -> int:
        """Number of changes that can be undone."""
        return sum(1 for c in self.changes if not c.reverted)

    def get_reversal_value(self, change: Change) -> tuple[ChangeType, str, Any]:
        """Get the values needed to reverse a change: (change_type, target, old_value)."""
        return (change.change_type, change.target, change.old_value)
