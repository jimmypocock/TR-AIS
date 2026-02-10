"""
Unit tests for Command Executor.

These tests verify the executor logic using mocked Ableton client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.executor import (
    CommandExecutor,
    ExecutionResult,
    ExecutionReport,
)


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = ExecutionResult(
            action="set_tempo",
            success=True,
            result={"tempo": 120}
        )
        assert result.success is True
        assert result.result == {"tempo": 120}
        assert result.error is None

    def test_error_result(self):
        """Test error result."""
        result = ExecutionResult(
            action="set_tempo",
            success=False,
            error="Connection lost"
        )
        assert result.success is False
        assert result.error == "Connection lost"


class TestExecutionReport:
    """Tests for ExecutionReport dataclass."""

    def test_empty_report(self):
        """Test empty report."""
        report = ExecutionReport()
        assert report.results == []
        assert report.success_count == 0
        assert report.error_count == 0
        assert report.all_success is False

    def test_all_success(self):
        """Test report with all successes."""
        report = ExecutionReport(
            results=[
                ExecutionResult("play", True),
                ExecutionResult("set_tempo", True, {"tempo": 120}),
            ],
            success_count=2,
            error_count=0
        )
        assert report.all_success is True

    def test_with_errors(self):
        """Test report with some errors."""
        report = ExecutionReport(
            results=[
                ExecutionResult("play", True),
                ExecutionResult("unknown", False, error="Unknown action"),
            ],
            success_count=1,
            error_count=1
        )
        assert report.all_success is False


class TestCommandExecutor:
    """Tests for CommandExecutor."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Ableton client."""
        client = MagicMock()

        # Mock transport
        client.transport = MagicMock()
        client.transport.play = AsyncMock()
        client.transport.stop = AsyncMock()
        client.transport.set_tempo = AsyncMock()
        client.transport.toggle_metronome = AsyncMock()

        # Mock tracks
        client.tracks = MagicMock()
        client.tracks.create_midi = AsyncMock(return_value=0)
        client.tracks.create_audio = AsyncMock(return_value=1)
        client.tracks.delete = AsyncMock()
        client.tracks.set_volume = AsyncMock()
        client.tracks.set_pan = AsyncMock()
        client.tracks.set_mute = AsyncMock()
        client.tracks.set_solo = AsyncMock()
        client.tracks.set_arm = AsyncMock()

        # Mock devices
        client.devices = MagicMock()
        client.devices.set_parameter = AsyncMock()

        return client

    @pytest.fixture
    def executor(self, mock_client):
        """Create executor with mock client."""
        return CommandExecutor(mock_client)

    @pytest.mark.asyncio
    async def test_execute_play(self, executor, mock_client):
        """Test executing play command."""
        commands = [{"action": "play", "params": {}}]
        report = await executor.execute(commands)

        assert report.success_count == 1
        assert report.error_count == 0
        mock_client.transport.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_stop(self, executor, mock_client):
        """Test executing stop command."""
        commands = [{"action": "stop", "params": {}}]
        report = await executor.execute(commands)

        assert report.success_count == 1
        mock_client.transport.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_set_tempo(self, executor, mock_client):
        """Test executing set_tempo command."""
        commands = [{"action": "set_tempo", "params": {"bpm": 120.0}}]
        report = await executor.execute(commands)

        assert report.success_count == 1
        mock_client.transport.set_tempo.assert_called_once_with(120.0)
        assert report.results[0].result == {"tempo": 120.0}

    @pytest.mark.asyncio
    async def test_execute_create_midi_track(self, executor, mock_client):
        """Test executing create_midi_track command."""
        commands = [{"action": "create_midi_track", "params": {"name": "Bass"}}]
        report = await executor.execute(commands)

        assert report.success_count == 1
        mock_client.tracks.create_midi.assert_called_once_with("Bass")
        assert report.results[0].result["name"] == "Bass"

    @pytest.mark.asyncio
    async def test_execute_set_track_volume(self, executor, mock_client):
        """Test executing set_track_volume command."""
        commands = [{"action": "set_track_volume", "params": {"track_index": 0, "volume": 0.5}}]
        report = await executor.execute(commands)

        assert report.success_count == 1
        mock_client.tracks.set_volume.assert_called_once_with(0, 0.5)

    @pytest.mark.asyncio
    async def test_execute_set_track_pan(self, executor, mock_client):
        """Test executing set_track_pan command."""
        commands = [{"action": "set_track_pan", "params": {"track_index": 1, "pan": -0.5}}]
        report = await executor.execute(commands)

        assert report.success_count == 1
        mock_client.tracks.set_pan.assert_called_once_with(1, -0.5)

    @pytest.mark.asyncio
    async def test_execute_set_device_parameter(self, executor, mock_client):
        """Test executing set_device_parameter command."""
        commands = [{
            "action": "set_device_parameter",
            "params": {
                "track_index": 0,
                "device_index": 1,
                "param_index": 3,
                "value": 0.7
            }
        }]
        report = await executor.execute(commands)

        assert report.success_count == 1
        mock_client.devices.set_parameter.assert_called_once_with(0, 1, 3, 0.7)

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, executor):
        """Test executing unknown action."""
        commands = [{"action": "unknown_action", "params": {}}]
        report = await executor.execute(commands)

        assert report.success_count == 0
        assert report.error_count == 1
        assert "No handler" in report.results[0].error

    @pytest.mark.asyncio
    async def test_execute_multiple_commands(self, executor, mock_client):
        """Test executing multiple commands."""
        commands = [
            {"action": "set_tempo", "params": {"bpm": 100}},
            {"action": "create_midi_track", "params": {"name": "Lead"}},
            {"action": "play", "params": {}},
        ]
        report = await executor.execute(commands)

        assert report.success_count == 3
        assert report.error_count == 0
        mock_client.transport.set_tempo.assert_called_once_with(100)
        mock_client.tracks.create_midi.assert_called_once_with("Lead")
        mock_client.transport.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self, executor, mock_client):
        """Test executor handles exceptions gracefully."""
        mock_client.transport.play.side_effect = Exception("Connection lost")

        commands = [{"action": "play", "params": {}}]
        report = await executor.execute(commands)

        assert report.success_count == 0
        assert report.error_count == 1
        assert "Connection lost" in report.results[0].error
