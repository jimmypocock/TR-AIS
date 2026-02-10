"""
Ableton Integration Package

This package provides a modular interface for controlling Ableton Live
via AbletonOSC.

Usage:
    from backend.ableton import AbletonClient, AbletonConfig

    client = AbletonClient()
    await client.connect()

    # Transport
    await client.transport.play()
    await client.transport.set_tempo(120)

    # Tracks
    await client.tracks.create_midi("Drums")
    await client.tracks.set_volume(0, 0.8)

    # Devices
    await client.devices.set_parameter(0, 0, 3, 0.7)

    client.disconnect()
"""

from .client import AbletonClient, AbletonConfig, SessionState
from .transport import TransportController
from .tracks import TrackController, Track
from .devices import DeviceController, Device, DeviceParameter

__all__ = [
    # Main client
    "AbletonClient",
    "AbletonConfig",
    "SessionState",
    # Controllers
    "TransportController",
    "TrackController",
    "DeviceController",
    # Data classes
    "Track",
    "Device",
    "DeviceParameter",
]
