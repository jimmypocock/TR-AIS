"""
Ableton AI Assistant Backend

This package provides the core functionality for AI-powered Ableton Live control.
"""

__version__ = "0.1.0"

from .config import Config, config
from .claude_engine import ClaudeEngine, ClaudeResponse
from .executor import CommandExecutor, ExecutionResult, ExecutionReport
from .session_cache import SessionCache, SessionState, CachedTrack, CachedDevice

__all__ = [
    "Config",
    "config",
    "ClaudeEngine",
    "ClaudeResponse",
    "CommandExecutor",
    "ExecutionResult",
    "ExecutionReport",
    "SessionCache",
    "SessionState",
    "CachedTrack",
    "CachedDevice",
]
