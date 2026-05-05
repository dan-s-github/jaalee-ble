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

from .parser import JaaleeBluetoothDeviceData, SensorModel

__version__ = "1.1.0-rc.1"

__all__ = [
    "BinarySensorDeviceClass",
    "BinarySensorValue",
    "DeviceKey",
    "JaaleeBluetoothDeviceData",
    "SensorDescription",
    "SensorDeviceClass",
    "SensorDeviceInfo",
    "SensorModel",
    "SensorUpdate",
    "SensorValue",
    "Units",
]
