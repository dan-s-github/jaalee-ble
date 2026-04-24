"""Parser for Jaalee BLE advertisements."""

from __future__ import annotations

from sensor_state_data import (
    BinarySensorDeviceClass,
    BinarySensorValue,
    DeviceKey,
    SensorDescription,
    SensorDeviceClass,
    SensorDeviceInfo,
    SensorUpdate,
    SensorValue,
    Units,
)

from .parser import JaaleeBluetoothDeviceData

__version__ = "1.0.0-rc.4"

__all__ = [
    "BinarySensorDeviceClass",
    "BinarySensorValue",
    "DeviceKey",
    "JaaleeBluetoothDeviceData",
    "SensorDescription",
    "SensorDeviceClass",
    "SensorDeviceInfo",
    "SensorUpdate",
    "SensorValue",
    "Units",
]
