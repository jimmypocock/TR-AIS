"""
Unit tests for Change Ledger.

These tests verify the change tracking and undo functionality.
"""

import pytest
from datetime import datetime

from backend.change_ledger import (
    ChangeLedger,
    Change,
    ChangeType,
)


class TestChange:
    """Tests for Change dataclass."""

    def test_create_change(self):
        """Test creating a change."""
        change = Change(
            id="abc123",
            timestamp=datetime.now(),
            change_type=ChangeType.TEMPO,
            target="transport",
            old_value=120.0,
            new_value=95.0,
            description="Changed tempo from 120 to 95 BPM",
        )
        assert change.id == "abc123"
        assert change.change_type == ChangeType.TEMPO
        assert change.old_value == 120.0
        assert change.new_value == 95.0
        assert change.reverted is False

    def test_to_dict(self):
        """Test converting change to dict."""
        change = Change(
            id="abc123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            change_type=ChangeType.TRACK_VOLUME,
            target="track:4",
            old_value=0.85,
            new_value=0.5,
            description="Set track 4 volume",
        )
        d = change.to_dict()
        assert d["id"] == "abc123"
        assert d["change_type"] == "track_volume"
        assert d["target"] == "track:4"
        assert d["old_value"] == 0.85
        assert d["new_value"] == 0.5


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_transport_types(self):
        """Test transport change types exist."""
        assert ChangeType.TEMPO
        assert ChangeType.PLAY_STATE
        assert ChangeType.METRONOME

    def test_track_types(self):
        """Test track change types exist."""
        assert ChangeType.TRACK_VOLUME
        assert ChangeType.TRACK_PAN
        assert ChangeType.TRACK_MUTE
        assert ChangeType.TRACK_SOLO
        assert ChangeType.TRACK_ARM
        assert ChangeType.TRACK_CREATE
        assert ChangeType.TRACK_DELETE

    def test_device_types(self):
        """Test device change types exist."""
        assert ChangeType.DEVICE_PARAMETER


class TestChangeLedger:
    """Tests for ChangeLedger."""

    @pytest.fixture
    def ledger(self):
        """Create empty ledger."""
        return ChangeLedger()

    def test_empty_ledger(self, ledger):
        """Test empty ledger state."""
        assert len(ledger.changes) == 0
        assert ledger.pending_count == 0
        assert ledger.get_undo_candidate() is None

    def test_record_change(self, ledger):
        """Test recording a change."""
        change = ledger.record(
            change_type=ChangeType.TEMPO,
            target="transport",
            old_value=120.0,
            new_value=95.0,
        )

        assert len(ledger.changes) == 1
        assert ledger.pending_count == 1
        assert change.old_value == 120.0
        assert change.new_value == 95.0
        assert len(change.id) == 8  # UUID prefix

    def test_auto_description_tempo(self, ledger):
        """Test auto-generated description for tempo."""
        change = ledger.record(
            change_type=ChangeType.TEMPO,
            target="transport",
            old_value=120.0,
            new_value=95.0,
        )
        assert "120" in change.description
        assert "95" in change.description
        assert "BPM" in change.description

    def test_auto_description_volume(self, ledger):
        """Test auto-generated description for volume."""
        change = ledger.record(
            change_type=ChangeType.TRACK_VOLUME,
            target="track:4",  # 0-indexed internal
            old_value=0.85,
            new_value=0.5,
        )
        assert "track 5" in change.description  # 1-indexed for display
        assert "85%" in change.description
        assert "50%" in change.description

    def test_auto_description_mute(self, ledger):
        """Test auto-generated description for mute."""
        change = ledger.record(
            change_type=ChangeType.TRACK_MUTE,
            target="track:2",  # 0-indexed internal
            old_value=False,
            new_value=True,
        )
        assert "Muted" in change.description
        assert "track 3" in change.description  # 1-indexed for display

    def test_custom_description(self, ledger):
        """Test custom description overrides auto."""
        change = ledger.record(
            change_type=ChangeType.TEMPO,
            target="transport",
            old_value=120.0,
            new_value=95.0,
            description="My custom description",
        )
        assert change.description == "My custom description"

    def test_get_undo_candidate(self, ledger):
        """Test getting undo candidate."""
        ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        ledger.record(ChangeType.TEMPO, "transport", 100, 90)

        candidate = ledger.get_undo_candidate()
        assert candidate is not None
        assert candidate.new_value == 90  # Most recent

    def test_get_undo_candidates(self, ledger):
        """Test getting multiple undo candidates."""
        ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        ledger.record(ChangeType.TEMPO, "transport", 100, 90)
        ledger.record(ChangeType.TEMPO, "transport", 90, 80)

        candidates = ledger.get_undo_candidates(2)
        assert len(candidates) == 2
        assert candidates[0].new_value == 80  # Most recent first
        assert candidates[1].new_value == 90

    def test_mark_reverted(self, ledger):
        """Test marking a change as reverted."""
        change = ledger.record(ChangeType.TEMPO, "transport", 120, 100)

        assert ledger.pending_count == 1
        result = ledger.mark_reverted(change.id)
        assert result is True
        assert change.reverted is True
        assert ledger.pending_count == 0

    def test_mark_reverted_not_found(self, ledger):
        """Test marking non-existent change."""
        result = ledger.mark_reverted("nonexistent")
        assert result is False

    def test_reverted_not_in_candidates(self, ledger):
        """Test reverted changes not returned as candidates."""
        change1 = ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        change2 = ledger.record(ChangeType.TEMPO, "transport", 100, 90)

        ledger.mark_reverted(change2.id)

        candidate = ledger.get_undo_candidate()
        assert candidate.id == change1.id  # Skip reverted

    def test_get_history(self, ledger):
        """Test getting history."""
        ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        ledger.record(ChangeType.TEMPO, "transport", 100, 90)
        ledger.record(ChangeType.TEMPO, "transport", 90, 80)

        history = ledger.get_history(limit=2)
        assert len(history) == 2
        assert history[0].new_value == 80  # Most recent first

    def test_get_history_include_reverted(self, ledger):
        """Test history includes reverted when asked."""
        change1 = ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        change2 = ledger.record(ChangeType.TEMPO, "transport", 100, 90)
        ledger.mark_reverted(change2.id)

        # Without reverted
        history = ledger.get_history(include_reverted=False)
        assert len(history) == 1

        # With reverted
        history = ledger.get_history(include_reverted=True)
        assert len(history) == 2

    def test_max_history_limit(self):
        """Test history is trimmed to max."""
        ledger = ChangeLedger(max_history=5)

        for i in range(10):
            ledger.record(ChangeType.TEMPO, "transport", i, i + 1)

        assert len(ledger.changes) == 5  # Trimmed to max

    def test_get_change_by_id(self, ledger):
        """Test getting change by ID."""
        change = ledger.record(ChangeType.TEMPO, "transport", 120, 100)

        found = ledger.get_change(change.id)
        assert found is not None
        assert found.id == change.id

    def test_get_change_not_found(self, ledger):
        """Test getting non-existent change."""
        found = ledger.get_change("nonexistent")
        assert found is None

    def test_clear(self, ledger):
        """Test clearing history."""
        ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        ledger.record(ChangeType.TEMPO, "transport", 100, 90)

        ledger.clear()
        assert len(ledger.changes) == 0
        assert ledger.pending_count == 0

    def test_get_reversal_value(self, ledger):
        """Test getting reversal info."""
        change = ledger.record(
            change_type=ChangeType.TRACK_VOLUME,
            target="track:4",
            old_value=0.85,
            new_value=0.5,
        )

        change_type, target, old_value = ledger.get_reversal_value(change)
        assert change_type == ChangeType.TRACK_VOLUME
        assert target == "track:4"
        assert old_value == 0.85


class TestChangeLedgerIntegration:
    """Integration-style tests for ledger scenarios."""

    def test_typical_session(self):
        """Test a typical session with multiple changes and undos."""
        ledger = ChangeLedger()

        # Make some changes
        c1 = ledger.record(ChangeType.TEMPO, "transport", 120, 100)
        c2 = ledger.record(ChangeType.TRACK_MUTE, "track:0", False, True)
        c3 = ledger.record(ChangeType.TRACK_VOLUME, "track:1", 0.85, 0.5)

        assert ledger.pending_count == 3

        # Undo last
        candidate = ledger.get_undo_candidate()
        assert candidate.id == c3.id
        ledger.mark_reverted(c3.id)

        assert ledger.pending_count == 2

        # Undo 2 more
        candidates = ledger.get_undo_candidates(2)
        assert len(candidates) == 2
        for c in candidates:
            ledger.mark_reverted(c.id)

        assert ledger.pending_count == 0

    def test_track_create_undo(self):
        """Test undoing track creation."""
        ledger = ChangeLedger()

        # Create track (old_value is None)
        change = ledger.record(
            change_type=ChangeType.TRACK_CREATE,
            target="track:5",
            old_value=None,
            new_value="New Synth",
        )

        change_type, target, old_value = ledger.get_reversal_value(change)
        assert change_type == ChangeType.TRACK_CREATE
        assert target == "track:5"
        assert old_value is None  # Means: delete the track
