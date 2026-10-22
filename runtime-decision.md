# Runtime decision: WAMR

Decision date: 2026-10-09. User-selected direction: replace MicroPython with
WAMR for host execution of daughter-board drivers. LLEXT is not the baseline
because native host/ABI coupling conflicts with portability across board revisions.

## Architectural commitments

- Store portable `.wasm` modules with a manifest in daughter-board NVM.
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

AOT remains an option if performance requires it and the target supports it.
If used, keep `.wasm` as the canonical daughter artifact and define a separate
compilation/provisioning path for target-specific artifacts. Do not assume a
small MCU can run the AOT compiler. Any host cache must be keyed by module hash,
target, runtime/compiler configuration, and Babel API compatibility.

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

No WAMR integration or timing qualification has been completed yet.
