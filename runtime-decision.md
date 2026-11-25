# Runtime decision: WAMR

Decision date: 2026-10-09. User-selected direction: replace MicroPython with
WAMR for host execution of daughter-board drivers. LLEXT is not the baseline
because native host/ABI coupling conflicts with portability across board revisions.

## Architectural commitments

- Store a WAMR AOT module with a manifest in daughter-board NVM (changed from
  portable `.wasm` on 2026-11-24; see below).
- Expose a small, versioned Babel API for complete bus transactions, events,
  timing services, and measurement delivery. Do not expose host OS structures,
  raw register addresses, or MCU pin numbers as the driver contract.
- Keep compatible API behavior across main-board revisions. Drivers declare
  required capabilities; hosts reject unsupported requirements before execution.
- Timing qualification belongs to each host/runtime configuration. Portability
  does not promise identical execution speed across processors.
- The host owns BLE, display, power, attachment generations, and peripheral
  resources. Driver cancellation must not depend on a successful guest cleanup.

## Implementation choices still open

Use C targeting wasm32 for the first experiment. This is a proposed toolchain,
not a requirement that every future driver be authored in C. Keep imports in a
versioned namespace such as `babel_v1`; begin without general WASI access.

Start evaluation with an interpreter so the daughter artifact can execute without
target-specific compilation. Pin a released WAMR version and verify its actual
features. Current upstream documentation describes interpreter instruction
metering, but excludes AOT/JIT from that mechanism. An instruction cap is not a
wall-clock deadline or a bound on native host calls.
[WAMR build configuration](https://github.com/wasm-micro-runtime/wasm-micro-runtime/blob/main/doc/build_wamr.md#instruction-metering).

## Update 2026-11-24: AOT-only daughter images (user decision)

Daughter EEPROM images now carry a **WAMR AOT module only**, compiled on a PC
with `wamrc` for the host's target. This replaces "portable `.wasm` canonical,
interpreter first". The host firmware is built AOT-only (no interpreter).

Consequences, accepted with the decision:

- An image runs only on the target and WAMR version it was compiled for. The
  manifest records both (`aot_target`, `wamr_version`); the host refuses a
  mismatch before loading. Changing the host chip or upgrading WAMR means
  rebuilding and reprogramming every daughter image.
- The `.wasm` remains the build intermediate in the repo, so an image can be
  regenerated for another target, but it is not stored on the daughter.
- WAMR's instruction metering covers the interpreter only, so AOT drivers have
  no instruction cap. A driver that loops forever hangs the host thread until a
  watchdog acts; execution limits for AOT are still open.

First result (2026-11-24, ESP32-S3 DevKitC + IR TH daughter rev A, WAMR 2.4.6,
wasi-sdk 34, `wamrc --target=xtensa --cpu=esp32s3` built against Espressif's
`xtensa_release_18.1.2` LLVM): the MLX90614 driver is 996 bytes of `.wasm` and
2,980 bytes of AOT; the whole image is 4,004 bytes (12% of the 24LC256). The
host loads it from the EEPROM, links `babel_v1`, and reads the sensor every
500 ms. Corrupt images and WAMR-version mismatches are refused before
programming. See `firmware/babel-host/README.md`.

Restrict memory growth and allocation during timing-critical work. Validate all
guest pointers, lengths, handles, and allowed bus addresses in native imports.
Set finite transaction deadlines and ensure native calls respond to cancellation.
WAMR specifically documents the need for native functions to cooperate with
termination.
[WAMR native API guidance](https://github.com/wasm-micro-runtime/wasm-micro-runtime/blob/main/doc/export_native_api.md#async-thread-termination).

For precise I/O, prefer host timer/capture/DMA or atomic transaction services
where supported. A timing-sensitive guest computation may also be feasible, but
requires worst-case execution and scheduling analysis for the chosen host.
Benchmark maxima alone do not prove hard deadlines. A daughter MCU remains an
option for requirements beyond host capabilities, not a universal requirement.

## Consequences and qualification

The previous Python class API and source-image format are superseded. The Wasm
ABI remains draft. The user subsequently selected ESP32-S3-WROOM-1-N8R8 as the
radio-board baseline (2026-10-17). The 32 KiB EEPROM capacity, host OS, execution
mode and resource budgets still require actual build results. The schematic does
not establish WAMR or BLE coexistence qualification.

Next experiment:

1. Compile a small sensor driver against a mock Babel bus API; load and invoke
   it through WAMR. Record toolchain/runtime versions and module/RAM sizes.
2. Exercise invalid memory access, infinite loops, missing imports, incompatible
   versions, and cancellation while inside a host transaction.
3. Run the same Wasm artifact on candidate embedded hosts. Verify real sensor
   transactions, BLE coexistence, and removal without resetting the host.
4. Define concrete deadline/jitter requirements for a representative demanding
   sensor, then assess worst-case behavior and hardware offload needs.
5. Freeze storage capacity and the initial API only after these results.

WAMR AOT integration runs on the bench (2026-11-24, above). Steps 2-5, BLE
coexistence and timing qualification have not been done.
