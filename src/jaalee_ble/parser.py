"""Parser for Jaalee BLE advertisements."""

from __future__ import annotations

import logging
from enum import Enum
from struct import Struct

from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData
from habluetooth import BluetoothServiceInfoBleak
from sensor_state_data import SensorDeviceClass, SensorLibrary, Units

_LOGGER = logging.getLogger(__name__)

# Apple company ID used by the Jaalee iBeacon advertisement format
_APPLE_COMPANY_ID = 0x004C

# Two-byte marker present at offset 16 within the Apple manufacturer data payload
# that identifies a Jaalee iBeacon advertisement (last two bytes of the proximity UUID).
_IBEACON_JAALEE_MARKER = b"\xf5\x25"
_IBEACON_MARKER_OFFSET = 16

# Expected length (bytes) of the Apple manufacturer data payload for the iBeacon format.
# Corresponds to a 28-byte raw AD structure: 1 length + 1 type + 2 company_id + 24 data.
_IBEACON_PAYLOAD_LEN = 24

# Expected lengths of the manufacturer data payload for the compact JHT format.
_COMPACT_PAYLOAD_LENS = frozenset({11, 12})

# Sensor key for the iBeacon Tx Power field (byte 22 of the Apple manufacturer payload).
_IBEACON_TX_POWER_KEY = "tx_power"

# Struct unpackers (big-endian)
_UNPACK_IBEACON = Struct(">HHbB").unpack  # raw_temp, raw_humi, tx_power, batt
_UNPACK_COMPACT = Struct(">HH").unpack  # raw_temp, raw_humi


class SensorModel(Enum):
    """Sensor model variant used to decode temperature/humidity values."""

    SHT20 = "sht20"
    SHT31 = "sht31"


def _decode_temp_humi(
    raw_temp: int, raw_humi: int, model: SensorModel = SensorModel.SHT20
) -> tuple[float, float]:
    """Convert Jaalee raw fixed-point values to °C and %RH."""
    if model is SensorModel.SHT31:
        # SHT31 datasheet (Sensirion): divisor is 2^16 - 1 = 65535
        temp = round(175.0 * raw_temp / 65535 - 45, 2)
        humi = round(100.0 * raw_humi / 65535, 2)
    else:
        # SHT20 datasheet (Sensirion): divisor is 2^16 = 65536
        temp = round(175.72 * raw_temp / 65536 - 46.85, 2)
        humi = round(125.0 * raw_humi / 65536 - 6, 2)
    return temp, humi


class JaaleeBluetoothDeviceData(BluetoothData):
    """Data parser for Jaalee Bluetooth devices."""

    def __init__(self, sensor_model: SensorModel = SensorModel.SHT20) -> None:
        super().__init__()
        self._sensor_model = sensor_model

    def _start_update(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Update from BLE advertisement data."""
        _LOGGER.debug("Parsing Jaalee BLE advertisement: %s", service_info)

        mfr_data = service_info.manufacturer_data
        if not mfr_data:
            return

        # iBeacon format: Apple company ID, 24-byte payload with Jaalee UUID marker
        apple_payload = mfr_data.get(_APPLE_COMPANY_ID)
        if (
            apple_payload is not None
            and len(apple_payload) == _IBEACON_PAYLOAD_LEN
            and apple_payload[_IBEACON_MARKER_OFFSET : _IBEACON_MARKER_OFFSET + 2]
            == _IBEACON_JAALEE_MARKER
        ):
            self._parse_ibeacon(apple_payload, service_info.address)
            return

        # Compact format: any company ID, 11 or 12-byte payload with embedded MAC
        for payload in mfr_data.values():
            if len(payload) in _COMPACT_PAYLOAD_LENS:
                if self._parse_compact(payload, service_info.address):
                    return

    def _parse_ibeacon(self, payload: bytes, address: str) -> None:
        """Parse the 24-byte Jaalee iBeacon manufacturer payload."""
        raw_temp, raw_humi, tx_power, batt = _UNPACK_IBEACON(payload[18:])
        temp, humi = _decode_temp_humi(raw_temp, raw_humi, self._sensor_model)

        self._setup_device(address)
        self.set_precision(2)
        self.update_predefined_sensor(SensorLibrary.TEMPERATURE__CELSIUS, temp)
        self.set_precision(2)
        self.update_predefined_sensor(SensorLibrary.HUMIDITY__PERCENTAGE, humi)
        self.set_precision(0)
        self.update_predefined_sensor(SensorLibrary.BATTERY__PERCENTAGE, batt)
        self.set_precision(0)
        self.update_sensor(
            key=_IBEACON_TX_POWER_KEY,
            native_unit_of_measurement=Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            native_value=tx_power,
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        )

    def _parse_compact(self, payload: bytes, address: str) -> bool:
        """
        Parse the 11 or 12-byte Jaalee compact manufacturer payload.

        The payload embeds the device MAC address for verification.
        Returns True if the embedded MAC matches the advertising device address.
        """
        batt = payload[0]
        mac_from_payload = payload[1:7][::-1]  # stored reversed; un-reverse it
        addr_bytes = bytes(int(b, 16) for b in address.split(":"))

        if mac_from_payload != addr_bytes:
            _LOGGER.debug(
                "Jaalee compact format MAC mismatch: device=%s payload=%s",
                address,
                ":".join(f"{b:02X}" for b in mac_from_payload),
            )
            return False

        raw_temp, raw_humi = _UNPACK_COMPACT(payload[-4:])
        temp, humi = _decode_temp_humi(raw_temp, raw_humi, self._sensor_model)

        self._setup_device(address)
        self.set_precision(2)
        self.update_predefined_sensor(SensorLibrary.TEMPERATURE__CELSIUS, temp)
        self.set_precision(2)
        self.update_predefined_sensor(SensorLibrary.HUMIDITY__PERCENTAGE, humi)
        self.set_precision(0)
        self.update_predefined_sensor(SensorLibrary.BATTERY__PERCENTAGE, batt)
        return True

    def _setup_device(self, address: str) -> None:
        """Set common device metadata."""
        short_addr = short_address(address)
        self.set_device_type("JHT")
        self.set_title(f"Jaalee {short_addr}")
        self.set_device_name(f"Jaalee {short_addr}")
        self.set_device_manufacturer("Jaalee")
