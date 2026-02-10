"""
Unit tests for Claude Engine.

These tests verify parsing and validation logic without calling the API.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.claude_engine import (
    ClaudeEngine,
    ClaudeResponse,
    AVAILABLE_ACTIONS,
    SYSTEM_PROMPT,
)


class TestClaudeResponse:
    """Tests for ClaudeResponse dataclass."""

    def test_default_values(self):
        """Test default response values."""
        response = ClaudeResponse()
        assert response.thinking == ""
        assert response.commands == []
        assert response.response == ""
        assert response.error is None

    def test_with_values(self):
        """Test response with values."""
        response = ClaudeResponse(
            thinking="User wants to create a track",
            commands=[{"action": "create_midi_track", "params": {"name": "Drums"}}],
            response="Created a Drums track.",
        )
        assert response.thinking == "User wants to create a track"
        assert len(response.commands) == 1
        assert response.response == "Created a Drums track."

    def test_with_error(self):
        """Test response with error."""
        response = ClaudeResponse(error="API error")
        assert response.error == "API error"


class TestAvailableActions:
    """Tests for available actions configuration."""

    def test_transport_actions_exist(self):
        """Test transport actions are defined."""
        assert "play" in AVAILABLE_ACTIONS
        assert "stop" in AVAILABLE_ACTIONS
        assert "set_tempo" in AVAILABLE_ACTIONS
        assert "toggle_metronome" in AVAILABLE_ACTIONS

    def test_track_actions_exist(self):
        """Test track actions are defined."""
        assert "create_midi_track" in AVAILABLE_ACTIONS
        assert "create_audio_track" in AVAILABLE_ACTIONS
        assert "delete_track" in AVAILABLE_ACTIONS
        assert "set_track_volume" in AVAILABLE_ACTIONS
        assert "set_track_pan" in AVAILABLE_ACTIONS
        assert "set_track_mute" in AVAILABLE_ACTIONS
        assert "set_track_solo" in AVAILABLE_ACTIONS

    def test_device_actions_exist(self):
        """Test device actions are defined."""
        assert "set_device_parameter" in AVAILABLE_ACTIONS

    def test_set_tempo_params(self):
        """Test set_tempo has correct params."""
        assert AVAILABLE_ACTIONS["set_tempo"]["params"] == ["bpm"]

    def test_create_midi_track_params(self):
        """Test create_midi_track has correct params."""
        assert AVAILABLE_ACTIONS["create_midi_track"]["params"] == ["name"]


class TestSystemPrompt:
    """Tests for system prompt content."""

    def test_prompt_not_empty(self):
        """Test system prompt is defined."""
        assert len(SYSTEM_PROMPT) > 0

    def test_prompt_includes_actions(self):
        """Test system prompt documents available actions."""
        assert "create_midi_track" in SYSTEM_PROMPT
        assert "set_tempo" in SYSTEM_PROMPT
        assert "set_track_volume" in SYSTEM_PROMPT

    def test_prompt_includes_json_format(self):
        """Test system prompt specifies JSON response format."""
        assert '"thinking"' in SYSTEM_PROMPT
        assert '"commands"' in SYSTEM_PROMPT
        assert '"response"' in SYSTEM_PROMPT


class TestClaudeEngineInit:
    """Tests for ClaudeEngine initialization."""

    def test_raises_without_api_key(self):
        """Test raises error when no API key provided."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("backend.claude_engine.config") as mock_config:
                mock_config.anthropic_api_key = ""
                with pytest.raises(ValueError) as exc:
                    ClaudeEngine()
                assert "API key" in str(exc.value)

    def test_accepts_api_key_parameter(self):
        """Test accepts API key as parameter."""
        with patch("anthropic.Anthropic"):
            engine = ClaudeEngine(api_key="test-key")
            assert engine.api_key == "test-key"


class TestClaudeEngineParseResponse:
    """Tests for response parsing logic."""

    @pytest.fixture
    def engine(self):
        """Create engine with mocked client."""
        with patch("anthropic.Anthropic"):
            return ClaudeEngine(api_key="test-key")

    def test_parse_valid_json(self, engine):
        """Test parsing valid JSON response."""
        text = '''{
            "thinking": "User wants tempo change",
            "commands": [{"action": "set_tempo", "params": {"bpm": 120}}],
            "response": "Set tempo to 120 BPM."
        }'''
        result = engine._parse_response(text)
        assert result.thinking == "User wants tempo change"
        assert len(result.commands) == 1
        assert result.response == "Set tempo to 120 BPM."
        assert result.error is None

    def test_parse_json_with_code_block(self, engine):
        """Test parsing JSON wrapped in code block."""
        text = '''Here's the response:
```json
{
    "thinking": "Creating track",
    "commands": [{"action": "create_midi_track", "params": {"name": "Bass"}}],
    "response": "Created Bass track."
}
```'''
        result = engine._parse_response(text)
        assert result.thinking == "Creating track"
        assert len(result.commands) == 1
        assert result.commands[0]["params"]["name"] == "Bass"

    def test_parse_json_with_generic_code_block(self, engine):
        """Test parsing JSON wrapped in generic code block."""
        text = '''```
{
    "thinking": "Test",
    "commands": [],
    "response": "Done."
}
```'''
        result = engine._parse_response(text)
        assert result.thinking == "Test"
        assert result.response == "Done."

    def test_parse_invalid_json(self, engine):
        """Test parsing invalid JSON returns error."""
        text = "This is not JSON at all"
        result = engine._parse_response(text)
        assert result.error is not None
        assert "Failed to parse" in result.error

    def test_parse_empty_commands(self, engine):
        """Test parsing response with empty commands."""
        text = '''{
            "thinking": "Cannot fulfill request",
            "commands": [],
            "response": "I don't know how to do that."
        }'''
        result = engine._parse_response(text)
        assert result.commands == []
        assert result.response == "I don't know how to do that."


class TestClaudeEngineValidateCommands:
    """Tests for command validation."""

    @pytest.fixture
    def engine(self):
        """Create engine with mocked client."""
        with patch("anthropic.Anthropic"):
            return ClaudeEngine(api_key="test-key")

    def test_validate_valid_command(self, engine):
        """Test validating a valid command."""
        commands = [{"action": "set_tempo", "params": {"bpm": 120}}]
        valid, errors = engine.validate_commands(commands)
        assert len(valid) == 1
        assert len(errors) == 0

    def test_validate_unknown_action(self, engine):
        """Test validating unknown action."""
        commands = [{"action": "unknown_action", "params": {}}]
        valid, errors = engine.validate_commands(commands)
        assert len(valid) == 0
        assert len(errors) == 1
        assert "Unknown action" in errors[0]

    def test_validate_missing_params(self, engine):
        """Test validating command with missing params."""
        commands = [{"action": "set_tempo", "params": {}}]  # Missing 'bpm'
        valid, errors = engine.validate_commands(commands)
        assert len(valid) == 0
        assert len(errors) == 1
        assert "missing params" in errors[0]

    def test_validate_multiple_commands(self, engine):
        """Test validating multiple commands."""
        commands = [
            {"action": "set_tempo", "params": {"bpm": 100}},
            {"action": "create_midi_track", "params": {"name": "Synth"}},
            {"action": "unknown", "params": {}},
        ]
        valid, errors = engine.validate_commands(commands)
        assert len(valid) == 2
        assert len(errors) == 1


class TestClaudeEngineBuildUserMessage:
    """Tests for building user message with context."""

    @pytest.fixture
    def engine(self):
        """Create engine with mocked client."""
        with patch("anthropic.Anthropic"):
            return ClaudeEngine(api_key="test-key")

    def test_message_with_no_state(self, engine):
        """Test building message without session state."""
        result = engine._build_user_message("create a track", {})
        assert "create a track" in result
        assert "Session State" not in result

    def test_message_with_state(self, engine):
        """Test building message with session state."""
        state = {"tempo": 120, "tracks": [{"name": "Drums"}]}
        result = engine._build_user_message("change tempo", state)
        assert "Session State" in result
        assert '"tempo": 120' in result
        assert "change tempo" in result
