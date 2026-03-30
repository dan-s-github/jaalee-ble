"""Parser for Jaalee BLE advertisements."""

from __future__ import annotations

from bluetooth_sensor_state_data import BluetoothData
from habluetooth import BluetoothServiceInfoBleak


class JaaleeBluetoothDeviceData(BluetoothData):
    """Data parser for Jaalee Bluetooth devices."""

    def _start_update(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Update from BLE advertisement data."""
        raise NotImplementedError
