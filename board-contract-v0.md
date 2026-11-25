# Babel board and software contract v0

Draft for implementation, updated 2026-10-09 for WAMR. These are proposed engineering choices,
not an existing supported protocol. See [architecture-proposal.md](architecture-proposal.md)
for the component rationale and electrical contract.

## Discovery and storage

The provisional storage profile exposes 32 KiB of 24LC256-compatible EEPROM at I2C address 0x50 on
the dedicated NVM bus. Use 16-bit byte addresses, high address byte first, and
100 kHz initially. Writes must split at 64-byte page boundaries and ACK-poll with
a bounded deadline. Hold write protection active outside explicit programming.

Capacity and this layout must be reevaluated after compiling representative Wasm
drivers. Reject oversized modules; never truncate them to fit. The Python-source
format is superseded; use a distinct magic/version to avoid interpreting old
payloads as Wasm. No deployed compatibility is assumed.

Single-image storage is sufficient for v0. Interrupted updates can leave the
board requiring reprogramming; they must never cause execution of an unverified
partial image. No automatic rollback is promised.

| Address | Size | Contents |
| --- | ---: | --- |
| 0x0000 | 64 bytes | Commit/header page |
| 0x0040 | 960 bytes | UTF-8 JSON manifest area, padded with 0xFF |
| 0x0400 | 28,672 bytes | Module area (format 3: WAMR AOT file), padded with 0xFF |
| 0x7400 | 3,072 bytes | Reserved; driver updater preserves this region |

Header integers are little-endian; I2C address bytes remain high-byte first.

| Header offset | Encoding | Meaning |
| --- | --- | --- |
| 0 | 8 bytes | Magic `BABELW01` |
| 8 | uint16 | Format version = 3 (WAMR AOT module; 2 was portable Wasm) |
| 10 | uint16 | Driver API version = 1 |
| 12 | uint16 | Manifest length, 1–960 |
| 14 | uint16 | Reserved = 0 |
| 16 | uint32 | Module length, 8–28,672 |
| 20 | 32 bytes | SHA-256 of header bytes 0–19 followed by exact manifest and module bytes |
| 52 | 12 bytes | Reserved = 0 |

Format 3 (2026-11-24) stores a WAMR AOT module instead of portable Wasm; the
layout is otherwise unchanged. Its manifest must add `"runtime": "wamr-aot"`,
`"aot_target"` (e.g. `"xtensa-esp32s3"`) and `"wamr_version"` (e.g. `"2.4.6"`),
and the host rejects any mismatch with its own target and WAMR build. The
manifest is stored as compact JSON exactly as hashed. Implemented by
`firmware/tools/babel_image.py` and `firmware/babel-host`.

Padding is excluded from the digest. A loader checks fixed fields and lengths
before allocating or reading payloads, then checks reserved bytes, digest, manifest
UTF-8/schema, API/capability compatibility, and Wasm validity before invocation.
Use WAMR validation plus host policy checks for imports, exports, memory, tables,
and supported Wasm features. Disallow a Wasm start section for this initial ABI,
so guest initialization only occurs through the budgeted explicit entry point.
SHA-256 here detects corruption; it does not authenticate trusted code.

Programming procedure: stop the driver, isolate sensor buses, deassert WP,
invalidate and read back the header magic, write manifest/module in pages,
read back and verify payload, write the final header page last, validate the full
image, then restore WP. Abort on removal, timeout, or verification failure. On
every exit restore a safe state; blank or invalid storage stays in provisioning
mode and can be rewritten without executing a driver.

## Manifest and driver API

Example IR manifest, subject to exact sensor selection:

```json
{
  "board_type": "babel.ir.mlx90632",
  "board_revision": 2,
  "driver_version": "0.1.0",
  "runtime": "wasm32-babel",
  "babel_api_major": 1,
  "required_capabilities": ["i2c.transfer.v1"],
  "name": "IR thermometer",
  "interface": {"kind": "i2c", "frequency_hz": 100000, "addresses": [58]},
  "power_ma": 10,
  "startup_ms": 500,
  "sample_period_ms": 500,
  "channels": [
    {"id": 0, "name": "object_temperature", "unit": "degC"},
    {"id": 1, "name": "ambient_temperature", "unit": "degC"}
  ]
}
```

The frequency, startup delay, power allocation, and default address are provisional
and must be verified for the selected part. Validate addresses as 7-bit unicast
addresses, channel IDs as unique bytes, strings as bounded, and interface kind
as exactly one of `i2c`, `spi`, or `uart`. Host-side limits override requested
frequency, startup delay, rate, and power. Reject requirements the host cannot
satisfy rather than silently relaxing them. The manifest API major must match
the header. Reject unsupported schemas/settings;
do not silently select another bus. Define SPI/UART-specific schema fields before
adding those daughter-board types. The current radio connector (2026-10-22) is
mirrored for reversible insertion and gives the sensor three general lines,
SENSOR_IO0-2 (I2C SCL/SDA/IRQ, UART TX/RX, or 3-wire/read-only SPI SCK/data/CS).
A manifest must fit in those three lines; reject one that needs more, such as
4-wire SPI.

The first implemented manifest, for the format-3 MLX90614 driver, is
`firmware/drivers/mlx90614/manifest.json`; the `wasm32-babel` example above
is the earlier format-2 form.

The first implementation of `babel_v1` (2026-11-24) is
`firmware/drivers/include/babel_v1.h`: `i2c_transfer` (write then read, each up
to 64 bytes, only to manifest addresses), `delay_ms` (clamped to 1 s),
`submit` (channel id, float) and `log`. Error codes: -1 argument, -2 address
not declared, -3 bus, -4 too many measurements in one poll.

Proposed Wasm exports, shown as C declarations:

```c
int32_t babel_driver_start(void);
int32_t babel_driver_poll(void);
int32_t babel_driver_stop(void);
```

Zero means success, a negative value means a driver error; `poll` may return 1
for no new sample. Imports in `babel_v1` provide complete bus transactions,
configuration access, and measurement submission. Native host pointers, OS
structures, and pin assignments never cross the ABI. Exact import signatures,
buffer layouts, numeric errors, and resource-limit fields must be specified and
tested before declaring this ABI implemented.

Host wrappers validate guest memory ranges and attachment generation, restrict
access to declared resources, serialize transactions, and enforce bus deadlines.
Measurements submitted during one poll are staged and published only after a
successful return; discard them on a trap, error, or removal. Polls with no data
must not submit measurements. Bound the staging buffer by declared channel count.

The host schedules calls and applies execution limits appropriate to the selected
WAMR mode. No background guest thread or driver-owned BLE/display operation is
part of v0. Memory isolation does not guarantee CPU availability or deadlines.
Resource limits and timing requirements need host-specific qualification; see
[runtime-decision.md](runtime-decision.md).

`babel_driver_stop()` must tolerate a missing board and is best-effort, budgeted
cleanup. Hardware isolation and result invalidation occur first. Cancel native
operations and wait until guest execution and callbacks have ceased before
freeing the instance or buffers. The host timestamps measurements and owns their
validity state; cleanup success is never required for electrical safety.

## Attachment state machine

`ABSENT → DEBOUNCE → POWERING → DISCOVERING → STARTING → RUNNING`

Provisional insertion debounce is 30 ms. Actual power-settle timing follows the
electrical design. Presence loss or power fault from any state disables signals,
cancels queued work, and invalidates the current session before optional cleanup.
Insertion delay is not a guarantee of contact sequencing.

Invalid storage enters `PROVISIONING`; invalid API or sensor initialization enters
`FAULT`. Neither executes unvalidated code. Explicit retry or a new insertion
starts discovery again; do not continually power-cycle a faulty board.

Allocate a new 32-bit session ID for each attachment attempt and whenever running
code is replaced. Discard results belonging to an older session. During one BLE
connection, session IDs must not be reused; reconnect before wraparound. A host
restart forces a new BLE connection and the app clears old state.

## BLE receiver protocol

Use a custom GATT service with a stable UUID and three characteristics. Assign
and record project UUIDs during codec implementation; names below are symbolic.

| Characteristic | Properties | Purpose |
| --- | --- | --- |
| Status | Read, notify | Protocol version, session, state, error code |
| Metadata | Read | Bounded JSON with board name and channel names/units |
| Measurement | Notify | One channel measurement per packet |

Set the metadata attribute's buffer explicitly. Limit it to 512 bytes and verify
long reads on the selected host BLE stack and Android implementation; use an
explicit chunk protocol if that test fails. Do not assume notification support
alone proves long-read support.

The measurement packet is exactly 20 bytes, little-endian, struct format
`<BBIHBBIf2x`:

| Offset | Type | Meaning |
| --- | --- | --- |
| 0 | uint8 | Protocol version = 1 |
| 1 | uint8 | Type = 1 (measurement) |
| 2 | uint32 | Attachment session |
| 6 | uint16 | Sample sequence, wraps modulo 65,536 |
| 8 | uint8 | Channel ID |
| 9 | uint8 | Flags, currently 0; reject unknown flags |
| 10 | uint32 | Milliseconds since session start, modulo 2^32 |
| 14 | float32 | Value in the channel's advertised unit |
| 18 | 2 bytes | Reserved = 0 |

The two reserved trailing bytes must be zero; decoders must check them explicitly
because struct padding is ignored when unpacking. Encode finite values only.
All channel values from one successful `babel_driver_poll()`
share a sequence and timestamp. Sequence gaps indicate missing samples, and
clients must also tolerate missing individual channels. Latest readings replace
older queued readings; the prototype is not a lossless logger.

Status is a 12-byte little-endian `<BBIBBHH` record: version, type=2, session,
state, error, metadata_revision, reserved=0. State IDs: 0 absent, 1 initializing,
2 running, 3 provisioning, 4 fault. Error IDs: 0 none, 1 storage, 2 incompatible,
3 sensor, 4 driver, 5 power. Unknown versions/states/errors are displayed as
unsupported rather than interpreted as success.

Metadata contains session, metadata_revision, board name, and channels. At
connect/reconnect subscribe to Status, read Status, read Metadata, then reread
Status and accept metadata only if session and revision still match. Subscribe
to measurements after that; discard packets until matching metadata exists and
status is running. A changed session clears readings immediately. Periodically
read Status as well (initial target: once per second) so a missed notification
does not leave stale attachment state forever. A BLE disconnect clears live state.

Metadata remains bounded and static within one session/revision. For an absent
or invalid board it reports no channels. The host keeps advertising and serving
status when there is no usable sensor.

## Validation before declaring v0 implemented

- Check storage region bounds, page splits, malformed JSON, invalid lengths,
  digest mismatch, unsupported API, truncated image, and interrupted writes.
- Check malformed Wasm, forbidden start sections, missing imports/exports,
  resource limits, memory traps, infinite loops, and cancellation in native calls.
- Check packet sizes, byte order, non-finite values, sequence wrap, session
  changes, and metadata/read races with shared host/Android fixtures.
- On actual hardware, remove the board during discovery, acquisition, and NVM
  programming. Confirm host uptime and electrical rail behavior, not just logs.
- Demonstrate a stuck sensor bus returns control; do not infer hang isolation
  from a passing exception test.
- Verify Android operation at the default ATT MTU and after reconnect. Larger
  MTUs are optional optimizations, not prerequisites for measurement packets.
