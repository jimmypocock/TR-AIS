"""
Command Executor for Ableton AI Assistant.

Takes structured commands from Claude and executes them via AbletonClient.
"""

from dataclasses import dataclass, field
from typing import Optional

from .ableton import AbletonClient


@dataclass
class ExecutionResult:
    """Result of executing a command."""
    action: str
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None


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
    """Executes Ableton commands from Claude."""

    def __init__(self, client: AbletonClient):
        """Initialize executor with an Ableton client.

        Args:
            client: Connected AbletonClient instance
        """
        self.client = client

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
        """Execute a single command.

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

            result = await handler(**params)
            return ExecutionResult(
                action=action,
                success=True,
                result=result
            )

        except Exception as e:
            return ExecutionResult(
                action=action,
                success=False,
                error=str(e)
            )

    # Transport handlers

    async def _do_play(self) -> dict:
        await self.client.transport.play()
        return {"status": "playing"}

    async def _do_stop(self) -> dict:
        await self.client.transport.stop()
        return {"status": "stopped"}

    async def _do_set_tempo(self, bpm: float) -> dict:
        await self.client.transport.set_tempo(bpm)
        return {"tempo": bpm}

    async def _do_toggle_metronome(self) -> dict:
        await self.client.transport.toggle_metronome()
        return {"metronome": "toggled"}

    # Track handlers

    async def _do_create_midi_track(self, name: str) -> dict:
        idx = await self.client.tracks.create_midi(name)
        return {"track_index": idx, "name": name, "type": "midi"}

    async def _do_create_audio_track(self, name: str) -> dict:
        idx = await self.client.tracks.create_audio(name)
        return {"track_index": idx, "name": name, "type": "audio"}

    async def _do_delete_track(self, track_index: int) -> dict:
        await self.client.tracks.delete(track_index)
        return {"deleted": track_index}

    async def _do_set_track_volume(self, track_index: int, volume: float) -> dict:
        await self.client.tracks.set_volume(track_index, volume)
        return {"track_index": track_index, "volume": volume}

    async def _do_set_track_pan(self, track_index: int, pan: float) -> dict:
        await self.client.tracks.set_pan(track_index, pan)
        return {"track_index": track_index, "pan": pan}

    async def _do_set_track_mute(self, track_index: int, muted: bool) -> dict:
        await self.client.tracks.set_mute(track_index, muted)
        return {"track_index": track_index, "muted": muted}

    async def _do_set_track_solo(self, track_index: int, soloed: bool) -> dict:
        await self.client.tracks.set_solo(track_index, soloed)
        return {"track_index": track_index, "soloed": soloed}

    async def _do_set_track_arm(self, track_index: int, armed: bool) -> dict:
        await self.client.tracks.set_arm(track_index, armed)
        return {"track_index": track_index, "armed": armed}

    # Device handlers

    async def _do_set_device_parameter(
        self,
        track_index: int,
        device_index: int,
        param_index: int,
        value: float
    ) -> dict:
        await self.client.devices.set_parameter(
            track_index, device_index, param_index, value
        )
        return {
            "track_index": track_index,
            "device_index": device_index,
            "param_index": param_index,
            "value": value
        }
