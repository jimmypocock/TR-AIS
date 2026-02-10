"""
Configuration management for Ableton AI Assistant.

Uses environment variables with sensible defaults.
Loads from .env file if present.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    anthropic_api_key: str = ""

    # Ableton OSC
    ableton_host: str = "127.0.0.1"
    ableton_send_port: int = 11000
    ableton_receive_port: int = 11001
    ableton_timeout: float = 1.0  # 1 sec is plenty for local OSC

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Paths
    plugins_dir: Path = Path("plugins")
    beat_machine_dir: Path = Path("beat-machine")

    # Claude
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            ableton_host=os.getenv("ABLETON_HOST", "127.0.0.1"),
            ableton_send_port=int(os.getenv("ABLETON_SEND_PORT", "11000")),
            ableton_receive_port=int(os.getenv("ABLETON_RECEIVE_PORT", "11001")),
            ableton_timeout=float(os.getenv("ABLETON_TIMEOUT", "5.0")),
            server_host=os.getenv("SERVER_HOST", "0.0.0.0"),
            server_port=int(os.getenv("SERVER_PORT", "8000")),
            plugins_dir=Path(os.getenv("PLUGINS_DIR", "plugins")),
            beat_machine_dir=Path(os.getenv("BEAT_MACHINE_DIR", "beat-machine")),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            claude_max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "4096")),
        )


# Global config instance
config = Config.from_env()
