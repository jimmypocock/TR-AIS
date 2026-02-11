"""
Command Executor for Ableton AI Assistant.

Takes structured commands from Claude and executes them via AbletonClient.
Records changes to a ledger for undo functionality.
"""

from dataclasses import dataclass, field
from typing import Optional

from .ableton import AbletonClient
from .change_ledger import ChangeLedger, ChangeType, Change


@dataclass
class ExecutionResult:
    """Result of executing a command."""
    action: str
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    change_id: Optional[str] = None  # ID of recorded change for undo


@dataclass
class ExecutionReport:
    """Report of executing multiple commands."""
    results: list[ExecutionResult] = field(default_factory=list)
    success_count: int = 0
    error_count: int = 0

    @property
    def all_success(self) -> bool:
        return self.error_count == 0 and self.success_count > 0


class CommandExecutor:
    """Executes Ableton commands from Claude with undo support."""

    def __init__(self, client: AbletonClient, ledger: ChangeLedger = None):
        """Initialize executor with an Ableton client.

        Args:
            client: Connected AbletonClient instance
            ledger: Optional ChangeLedger for undo support
        """
        self.client = client
        self.ledger = ledger or ChangeLedger()

    async def execute(self, commands: list) -> ExecutionReport:
        """Execute a list of commands.

        Args:
            commands: List of command dicts with 'action' and 'params'

        Returns:
            ExecutionReport with results for each command
        """
        report = ExecutionReport()

        for cmd in commands:
            action = cmd.get("action")
            params = cmd.get("params", {})

            result = await self._execute_one(action, params)
            report.results.append(result)

            if result.success:
                report.success_count += 1
            else:
                report.error_count += 1

        return report

    async def _execute_one(self, action: str, params: dict) -> ExecutionResult:
        """Execute a single command with ledger recording.

        Args:
            action: Action name
            params: Action parameters

        Returns:
            ExecutionResult
        """
        try:
            handler = getattr(self, f"_do_{action}", None)
            if handler is None:
                return ExecutionResult(
                    action=action,
                    success=False,
                    error=f"No handler for action: {action}"
                )

            # Execute and get result (handler records to ledger)
            result, change = await handler(**params)

            return ExecutionResult(
                action=action,
                success=True,
                result=result,
                change_id=change.id if change else None
            )

        except Exception as e:
            return ExecutionResult(
                action=action,
                success=False,
                error=str(e)
            )

    async def undo(self, count: int = 1) -> list[ExecutionResult]:
        """
        Undo the last N changes.

        Args:
            count: Number of changes to undo

        Returns:
            List of ExecutionResults for each undo operation
        """
        results = []
        candidates = self.ledger.get_undo_candidates(count)

        for change in candidates:
            result = await self._undo_change(change)
            results.append(result)

        return results

    async def _undo_change(self, change: Change) -> ExecutionResult:
        """
        Undo a specific change.

        Args:
            change: The Change to undo

        Returns:
            ExecutionResult
        """
        try:
            # Get the reversal info
            change_type, target, old_value = self.ledger.get_reversal_value(change)

            # Execute the reversal based on type
            if change_type == ChangeType.TEMPO:
                await self.client.transport.set_tempo(old_value)

            elif change_type == ChangeType.TRACK_VOLUME:
                track_idx = int(target.split(":")[1])
                await self.client.tracks.set_volume(track_idx, old_value)

            elif change_type == ChangeType.TRACK_PAN:
                track_idx = int(target.split(":")[1])
                await self.client.tracks.set_pan(track_idx, old_value)

            elif change_type == ChangeType.TRACK_MUTE:
                track_idx = int(target.split(":")[1])
                await self.client.tracks.set_mute(track_idx, old_value)

            elif change_type == ChangeType.TRACK_SOLO:
                track_idx = int(target.split(":")[1])
                await self.client.tracks.set_solo(track_idx, old_value)

            elif change_type == ChangeType.TRACK_ARM:
                track_idx = int(target.split(":")[1])
                await self.client.tracks.set_arm(track_idx, old_value)

            elif change_type == ChangeType.TRACK_CREATE:
                # old_value is None, target has track index, delete it
                track_idx = int(target.split(":")[1])
                await self.client.tracks.delete(track_idx)

            elif change_type == ChangeType.DEVICE_PARAMETER:
                parts = target.split(":")
                track_idx = int(parts[1])
                device_idx = int(parts[3])
                param_idx = int(parts[5])
                await self.client.devices.set_parameter(track_idx, device_idx, param_idx, old_value)

            else:
                return ExecutionResult(
                    action="undo",
                    success=False,
                    error=f"Cannot undo change type: {change_type}"
                )

            # Mark as reverted
            self.ledger.mark_reverted(change.id)

            return ExecutionResult(
                action="undo",
                success=True,
                result={"undone": change.description, "change_id": change.id}
            )

        except Exception as e:
            return ExecutionResult(
                action="undo",
                success=False,
                error=f"Failed to undo: {e}"
            )

    # --- Transport handlers ---

    async def _do_play(self) -> tuple[dict, Optional[Change]]:
        await self.client.transport.play()
        # Play/stop not really undoable in a meaningful way
        return {"status": "playing"}, None

    async def _do_stop(self) -> tuple[dict, Optional[Change]]:
        await self.client.transport.stop()
        return {"status": "stopped"}, None

    async def _do_set_tempo(self, bpm: float) -> tuple[dict, Optional[Change]]:
        # Get current tempo first
        old_tempo = await self.client.transport.get_tempo() or 120.0

        await self.client.transport.set_tempo(bpm)

        change = self.ledger.record(
            change_type=ChangeType.TEMPO,
            target="transport",
            old_value=old_tempo,
            new_value=bpm,
        )

        return {"tempo": bpm, "previous": old_tempo}, change

    async def _do_toggle_metronome(self) -> tuple[dict, Optional[Change]]:
        await self.client.transport.toggle_metronome()
        return {"metronome": "toggled"}, None

    # --- Track handlers ---

    async def _do_create_midi_track(self, name: str) -> tuple[dict, Optional[Change]]:
        idx = await self.client.tracks.create_midi(name)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_CREATE,
            target=f"track:{idx}",
            old_value=None,
            new_value=name,
        )

        return {"track_index": idx, "name": name, "type": "midi"}, change

    async def _do_create_audio_track(self, name: str) -> tuple[dict, Optional[Change]]:
        idx = await self.client.tracks.create_audio(name)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_CREATE,
            target=f"track:{idx}",
            old_value=None,
            new_value=name,
        )

        return {"track_index": idx, "name": name, "type": "audio"}, change

    async def _do_delete_track(self, track_index: int) -> tuple[dict, Optional[Change]]:
        # Note: Track deletion is harder to undo (would need to recreate with same content)
        # For now, we don't record it as undoable
        await self.client.tracks.delete(track_index)
        return {"deleted": track_index}, None

    async def _do_set_track_volume(self, track_index: int, volume: float) -> tuple[dict, Optional[Change]]:
        # Get current volume first
        old_volume = await self.client.tracks.get_volume(track_index) or 0.85

        await self.client.tracks.set_volume(track_index, volume)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_VOLUME,
            target=f"track:{track_index}",
            old_value=old_volume,
            new_value=volume,
        )

        return {"track_index": track_index, "volume": volume, "previous": old_volume}, change

    async def _do_set_track_pan(self, track_index: int, pan: float) -> tuple[dict, Optional[Change]]:
        old_pan = await self.client.tracks.get_pan(track_index) or 0.0

        await self.client.tracks.set_pan(track_index, pan)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_PAN,
            target=f"track:{track_index}",
            old_value=old_pan,
            new_value=pan,
        )

        return {"track_index": track_index, "pan": pan, "previous": old_pan}, change

    async def _do_set_track_mute(self, track_index: int, muted: bool) -> tuple[dict, Optional[Change]]:
        old_muted = await self.client.tracks.get_mute(track_index) or False

        await self.client.tracks.set_mute(track_index, muted)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_MUTE,
            target=f"track:{track_index}",
            old_value=old_muted,
            new_value=muted,
        )

        return {"track_index": track_index, "muted": muted, "previous": old_muted}, change

    async def _do_set_track_solo(self, track_index: int, soloed: bool) -> tuple[dict, Optional[Change]]:
        old_soloed = await self.client.tracks.get_solo(track_index) or False

        await self.client.tracks.set_solo(track_index, soloed)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_SOLO,
            target=f"track:{track_index}",
            old_value=old_soloed,
            new_value=soloed,
        )

        return {"track_index": track_index, "soloed": soloed, "previous": old_soloed}, change

    async def _do_set_track_arm(self, track_index: int, armed: bool) -> tuple[dict, Optional[Change]]:
        old_armed = await self.client.tracks.get_arm(track_index) or False

        await self.client.tracks.set_arm(track_index, armed)

        change = self.ledger.record(
            change_type=ChangeType.TRACK_ARM,
            target=f"track:{track_index}",
            old_value=old_armed,
            new_value=armed,
        )

        return {"track_index": track_index, "armed": armed, "previous": old_armed}, change

    # --- Device handlers ---

    async def _do_set_device_parameter(
        self,
        track_index: int,
        device_index: int,
        param_index: int,
        value: float
    ) -> tuple[dict, Optional[Change]]:
        # Get current value first
        old_value = await self.client.devices.get_parameter(track_index, device_index, param_index) or 0.0

        await self.client.devices.set_parameter(track_index, device_index, param_index, value)

        change = self.ledger.record(
            change_type=ChangeType.DEVICE_PARAMETER,
            target=f"track:{track_index}:device:{device_index}:param:{param_index}",
            old_value=old_value,
            new_value=value,
        )

        return {
            "track_index": track_index,
            "device_index": device_index,
            "param_index": param_index,
            "value": value,
            "previous": old_value
        }, change
