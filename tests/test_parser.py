"""Tests for the Jaalee BLE parser."""

from __future__ import annotations

import struct
from uuid import UUID

from bleak.backends.device import BLEDevice
from bluetooth_data_tools import monotonic_time_coarse
from habluetooth import BluetoothServiceInfoBleak

from jaalee_ble import JaaleeBluetoothDeviceData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEVICE_ADDRESS = "AA:BB:CC:DD:EE:FF"
DEVICE_NAME = "Jaalee_EEFF"

# iBeacon format constants
# Jaalee marker sits at byte offset 16 of the Apple manufacturer payload.
_IBEACON_MARKER = b"\xf5\x25"

# Compact format: MAC stored reversed in bytes [1:7] of the payload.
_MAC_REVERSED = bytes([0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA])

# Precomputed raw values for temp=25.0°C, humi=60.0%, batt=85
#   raw_temp = 26214  →  round(175 * 26214 / 65535 - 45, 2) = 25.0
#   raw_humi = 39321  →  round(100 * 39321 / 65535, 2)       = 60.0
RAW_TEMP_25 = 26214  # 0x6666
RAW_HUMI_60 = 39321  # 0x9999
BATT_85 = 85

# Precomputed raw values for temp=20.0°C, humi=50.0%, batt=72
#   raw_temp = 24341  →  round(175 * 24341 / 65535 - 45, 2) = 20.0
#   raw_humi = 32768  →  round(100 * 32768 / 65535, 2)       = 50.0
RAW_TEMP_20 = 24341  # 0x5F15
RAW_HUMI_50 = 32768  # 0x8000
BATT_72 = 72


def make_service_info(
    address: str = DEVICE_ADDRESS,
    name: str = DEVICE_NAME,
    manufacturer_data: dict[int, bytes] | None = None,
    rssi: int = -60,
) -> BluetoothServiceInfoBleak:
    """Create a BluetoothServiceInfoBleak instance for testing."""
    return BluetoothServiceInfoBleak(
        name=name,
        address=address,
        rssi=rssi,
        service_uuids=[],
        service_data={},
        manufacturer_data=manufacturer_data or {},
        device=BLEDevice(address=address, name=name, details={}),
        advertisement=None,
        connectable=True,
        time=monotonic_time_coarse(),
        source="local",
        tx_power=0,
    )


def make_ibeacon_payload(
    raw_temp: int = RAW_TEMP_25,
    raw_humi: int = RAW_HUMI_60,
    batt: int = BATT_85,
    reserved: int = 0,
) -> bytes:
    """Build a 24-byte Apple manufacturer payload in Jaalee iBeacon format.

    Layout:
      [0:16]  – iBeacon preamble / proximity UUID prefix (arbitrary)
      [16:18] – Jaalee UUID marker (0xF5, 0x25)
      [18:20] – raw temperature (big-endian uint16)
      [20:22] – raw humidity   (big-endian uint16)
      [22]    – reserved byte
      [23]    – battery percent
    """
    prefix = b"\x02\x15" + b"\x00" * 14  # 16 bytes: iBeacon type+length + UUID prefix
    sensor = struct.pack(">HHBB", raw_temp, raw_humi, reserved, batt)
    return prefix + _IBEACON_MARKER + sensor  # 16 + 2 + 6 = 24 bytes


def make_compact_payload(
    mac_reversed: bytes = _MAC_REVERSED,
    raw_temp: int = RAW_TEMP_20,
    raw_humi: int = RAW_HUMI_50,
    batt: int = BATT_72,
    extra: bytes = b"",
) -> bytes:
    """Build an 11 or 12-byte compact manufacturer payload.

    Layout:
      [0]    – battery percent
      [1:7]  – device MAC address stored in reverse byte order
      [7:9]  – raw temperature (big-endian uint16)
      [9:11] – raw humidity   (big-endian uint16)
      [11]   – optional extra byte (for 12-byte variant)
    """
    sensor = struct.pack(">HH", raw_temp, raw_humi)
    return bytes([batt]) + mac_reversed + extra + sensor


# ---------------------------------------------------------------------------
# Tests – iBeacon format
# ---------------------------------------------------------------------------


def test_ibeacon_format_parses_temperature_humidity_battery() -> None:
    """iBeacon advertisement yields correct temp, humi, and battery."""
    service_info = make_service_info(
        manufacturer_data={0x004C: make_ibeacon_payload()}
    )

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert result.title == "Jaalee EEFF"
    assert result.devices[None].name == "Jaalee EEFF"
    assert result.devices[None].manufacturer == "Jaalee"
    assert result.devices[None].model == "JHT"

    values = {k.key: v.native_value for k, v in result.entity_values.items()}
    assert values["temperature"] == 25.0
    assert values["humidity"] == 60.0
    assert values["battery"] == 85


def test_ibeacon_format_wrong_marker_ignored() -> None:
    """Apple manufacturer data with the wrong UUID marker is not parsed."""
    payload = bytearray(make_ibeacon_payload())
    payload[16] = 0x00  # corrupt the Jaalee marker
    service_info = make_service_info(manufacturer_data={0x004C: bytes(payload)})

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert not result.entity_values


def test_ibeacon_format_wrong_payload_length_ignored() -> None:
    """Apple manufacturer data of unexpected length is not parsed."""
    service_info = make_service_info(
        manufacturer_data={0x004C: make_ibeacon_payload()[:-1]}  # 23 bytes, not 24
    )

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert not result.entity_values


# ---------------------------------------------------------------------------
# Tests – compact format
# ---------------------------------------------------------------------------


def test_compact_format_11_bytes_parses_correctly() -> None:
    """11-byte compact advertisement yields correct temp, humi, and battery."""
    service_info = make_service_info(
        manufacturer_data={0x05D8: make_compact_payload()}
    )

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert result.title == "Jaalee EEFF"
    assert result.devices[None].manufacturer == "Jaalee"
    assert result.devices[None].model == "JHT"

    values = {k.key: v.native_value for k, v in result.entity_values.items()}
    assert values["temperature"] == 20.0
    assert values["humidity"] == 50.0
    assert values["battery"] == 72


def test_compact_format_12_bytes_parses_correctly() -> None:
    """12-byte compact advertisement (with trailing byte) parses correctly."""
    service_info = make_service_info(
        manufacturer_data={0x05D8: make_compact_payload(extra=b"\x00")}
    )

    result = JaaleeBluetoothDeviceData().update(service_info)

    values = {k.key: v.native_value for k, v in result.entity_values.items()}
    assert values["temperature"] == 20.0
    assert values["humidity"] == 50.0
    assert values["battery"] == 72


def test_compact_format_mac_mismatch_returns_no_data() -> None:
    """Compact advertisement whose embedded MAC mismatches the device is ignored."""
    wrong_mac_reversed = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
    service_info = make_service_info(
        manufacturer_data={0x05D8: make_compact_payload(mac_reversed=wrong_mac_reversed)}
    )

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert not result.entity_values


# ---------------------------------------------------------------------------
# Tests – edge cases
# ---------------------------------------------------------------------------


def test_no_manufacturer_data_returns_no_data() -> None:
    """Advertisement with no manufacturer data produces no sensor values."""
    service_info = make_service_info(manufacturer_data={})

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert not result.entity_values


def test_unrecognised_manufacturer_data_returns_no_data() -> None:
    """Manufacturer data that matches no known format is silently ignored."""
    service_info = make_service_info(
        manufacturer_data={0x1234: bytes(8)}  # 8 bytes – not 11, 12, or 24
    )

    result = JaaleeBluetoothDeviceData().update(service_info)

    assert not result.entity_values
