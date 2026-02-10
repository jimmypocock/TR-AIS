"""
Device Controller - Manage devices and their parameters.

Handles all device-related operations in Ableton Live, including
instruments, effects, and their parameters.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AbletonClient


@dataclass
class DeviceParameter:
    """Represents a device parameter."""
    index: int
    name: str
    value: float
    min: float
    max: float
    is_quantized: bool = False


@dataclass
class Device:
    """Represents an Ableton device (instrument or effect)."""
    track_index: int
    device_index: int
    name: str
    class_name: str = ""
    type: str = ""  # "instrument", "audio_effect", "midi_effect"
    parameters: list[DeviceParameter] = field(default_factory=list)


class DeviceController:
    """
    Controls Ableton's devices and their parameters.

    Usage:
        # Get device info
        name = await client.devices.get_name(track=0, device=0)
        params = await client.devices.get_parameter_names(track=0, device=0)

        # Set parameters
        await client.devices.set_parameter(track=0, device=0, param=3, value=0.7)

        # Get parameter info
        value = await client.devices.get_parameter(track=0, device=0, param=3)
    """

    def __init__(self, client: "AbletonClient"):
        self._client = client

    # --- Device Info ---

    async def get_count(self, track_index: int) -> Optional[int]:
        """Get number of devices on a track."""
        result = await self._client.send_and_wait(
            "/live/track/get/num_devices", track_index,
            response_address="/live/track/get/num_devices"
        )
        return int(result[1]) if result and len(result) > 1 else None

    async def get_name(self, track_index: int, device_index: int) -> Optional[str]:
        """Get device name."""
        result = await self._client.send_and_wait(
            "/live/device/get/name", track_index, device_index,
            response_address="/live/device/get/name"
        )
        return str(result[2]) if result and len(result) > 2 else None

    async def get_class_name(self, track_index: int, device_index: int) -> Optional[str]:
        """Get device class name (e.g., 'Wavetable', 'Compressor')."""
        result = await self._client.send_and_wait(
            "/live/device/get/class_name", track_index, device_index,
            response_address="/live/device/get/class_name"
        )
        return str(result[2]) if result and len(result) > 2 else None

    async def get_type(self, track_index: int, device_index: int) -> Optional[str]:
        """Get device type."""
        result = await self._client.send_and_wait(
            "/live/device/get/type", track_index, device_index,
            response_address="/live/device/get/type"
        )
        return str(result[2]) if result and len(result) > 2 else None

    # --- Parameters ---

    async def get_parameter_count(self, track_index: int, device_index: int) -> Optional[int]:
        """Get number of parameters exposed by the device."""
        result = await self._client.send_and_wait(
            "/live/device/get/num_parameters", track_index, device_index,
            response_address="/live/device/get/num_parameters"
        )
        return int(result[2]) if result and len(result) > 2 else None

    async def get_parameter_names(self, track_index: int, device_index: int) -> Optional[list[str]]:
        """Get all parameter names for a device."""
        result = await self._client.send_and_wait(
            "/live/device/get/parameters/name", track_index, device_index,
            response_address="/live/device/get/parameters/name"
        )
        # Response is: track_id, device_id, [names...]
        return list(result[2:]) if result and len(result) > 2 else None

    async def get_parameter_values(self, track_index: int, device_index: int) -> Optional[list[float]]:
        """Get all parameter values for a device."""
        result = await self._client.send_and_wait(
            "/live/device/get/parameters/value", track_index, device_index,
            response_address="/live/device/get/parameters/value"
        )
        return [float(v) for v in result[2:]] if result and len(result) > 2 else None

    async def get_parameter_ranges(self, track_index: int, device_index: int) -> Optional[dict]:
        """Get min/max ranges for all parameters."""
        min_result = await self._client.send_and_wait(
            "/live/device/get/parameters/min", track_index, device_index,
            response_address="/live/device/get/parameters/min"
        )
        max_result = await self._client.send_and_wait(
            "/live/device/get/parameters/max", track_index, device_index,
            response_address="/live/device/get/parameters/max"
        )

        if min_result and max_result and len(min_result) > 2 and len(max_result) > 2:
            mins = [float(v) for v in min_result[2:]]
            maxs = [float(v) for v in max_result[2:]]
            return {"min": mins, "max": maxs}
        return None

    async def get_parameter(
        self,
        track_index: int,
        device_index: int,
        param_index: int
    ) -> Optional[float]:
        """Get a single parameter value."""
        result = await self._client.send_and_wait(
            "/live/device/get/parameter/value",
            track_index, device_index, param_index,
            response_address="/live/device/get/parameter/value"
        )
        return float(result[3]) if result and len(result) > 3 else None

    async def get_parameter_string(
        self,
        track_index: int,
        device_index: int,
        param_index: int
    ) -> Optional[str]:
        """Get parameter value as formatted string (e.g., '2500 Hz')."""
        result = await self._client.send_and_wait(
            "/live/device/get/parameter/value_string",
            track_index, device_index, param_index,
            response_address="/live/device/get/parameter/value_string"
        )
        return str(result[3]) if result and len(result) > 3 else None

    async def set_parameter(
        self,
        track_index: int,
        device_index: int,
        param_index: int,
        value: float
    ):
        """Set a single parameter value."""
        self._client.send(
            "/live/device/set/parameter/value",
            track_index, device_index, param_index, float(value)
        )

    async def set_parameters(
        self,
        track_index: int,
        device_index: int,
        values: list[float]
    ):
        """Set multiple parameter values at once."""
        self._client.send(
            "/live/device/set/parameters/value",
            track_index, device_index, *[float(v) for v in values]
        )

    # --- Device State ---

    async def get_enabled(self, track_index: int, device_index: int) -> Optional[bool]:
        """Check if device is enabled (not bypassed)."""
        result = await self._client.send_and_wait(
            "/live/device/get/is_active", track_index, device_index,
            response_address="/live/device/get/is_active"
        )
        return bool(result[2]) if result and len(result) > 2 else None

    # --- Full Device Info ---

    async def get_device_info(self, track_index: int, device_index: int) -> Optional[Device]:
        """Get complete device information including all parameters."""
        name = await self.get_name(track_index, device_index)
        if not name:
            return None

        class_name = await self.get_class_name(track_index, device_index)
        device_type = await self.get_type(track_index, device_index)
        param_names = await self.get_parameter_names(track_index, device_index)
        param_values = await self.get_parameter_values(track_index, device_index)
        param_ranges = await self.get_parameter_ranges(track_index, device_index)

        parameters = []
        if param_names and param_values:
            for i, (pname, pvalue) in enumerate(zip(param_names, param_values)):
                param = DeviceParameter(
                    index=i,
                    name=str(pname),
                    value=float(pvalue),
                    min=param_ranges["min"][i] if param_ranges else 0.0,
                    max=param_ranges["max"][i] if param_ranges else 1.0,
                )
                parameters.append(param)

        return Device(
            track_index=track_index,
            device_index=device_index,
            name=name,
            class_name=class_name or "",
            type=device_type or "",
            parameters=parameters,
        )
