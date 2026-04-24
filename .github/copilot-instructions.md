# Copilot instructions for `jaalee-ble`

## Build, test, and lint commands

- Install dependencies with `uv sync`.
- Run the full test suite with `uv run pytest`.
- Run a single test with `uv run pytest tests/test_parser.py::test_compact_format_11_bytes_parses_correctly`.
- Run linting/formatting/type checks with `uv run pre-commit run -a`.
- Build the package with `uv build`.
- If you touch documentation tooling, install docs dependencies with `uv sync --group docs` and build docs with `uv run --group docs sphinx-build -b html docs docs/_build/html`.

## High-level architecture

- The public package surface is intentionally small. `src/jaalee_ble/__init__.py` mostly re-exports `sensor_state_data` types and exposes `JaaleeBluetoothDeviceData`.
- The actual library logic lives in `src/jaalee_ble/parser.py`. `JaaleeBluetoothDeviceData` subclasses `bluetooth_sensor_state_data.BluetoothData`, and `_start_update()` is the advertisement entrypoint.
- `_start_update()` supports two manufacturer-data formats:
  - **Jaalee iBeacon format**: Apple company ID `0x004C`, payload length `24`, and Jaalee marker `b"\xf5\x25"` at byte offset `16`. Sensor bytes are unpacked from `payload[18:]`.
  - **Compact Jaalee format**: any manufacturer payload of length `11` or `12`. Byte `0` is battery, bytes `1:7` are the reversed MAC address, and the last 4 bytes contain raw temperature/humidity.
- Both formats feed shared helpers: `_decode_temp_humi()` converts raw fixed-point values to Celsius and relative humidity, while `_setup_device()` normalizes metadata to manufacturer `Jaalee`, model `JHT`, and title/device name `Jaalee {short_address}`.
- Sensor entities are produced through `SensorLibrary` predefined sensors, with explicit precision changes before each update: temperature and humidity use precision `2`, battery uses precision `0`.
- Tests in `tests/test_parser.py` build synthetic `BluetoothServiceInfoBleak` advertisements and assert on `SensorUpdate` output rather than using live BLE hardware.
- `conftest.py` enables Sybil for `*.md`, `*.rst`, and `*.py`, so documentation snippets are part of the pytest suite. `docs/index.md` includes the README, and `docs/conf.py` runs `sphinx-apidoc` automatically at doc-build time.

## Key conventions

- Keep parser behavior centralized in `src/jaalee_ble/parser.py`; new advertisement handling should reuse `_decode_temp_humi()` and `_setup_device()` instead of duplicating sensor or metadata setup.
- Unsupported payloads are ignored by returning no entity values. For the compact format, MAC validation is required before decoding sensor bytes.
- Parser tests follow the existing pattern of constructing raw manufacturer payloads with helper factories and asserting `result.entity_values` by sensor key.
- Documentation changes can break pytest because Sybil collects Markdown/ReST examples. Treat README and docs edits as test-impacting changes.
- The project uses Conventional Commits (`commitlint` runs in CI), and releases are driven by `python-semantic-release`, with version values kept in sync across `pyproject.toml`, `src/jaalee_ble/__init__.py`, and `docs/conf.py`.
