# babel-host (ESP-IDF + WAMR AOT)

Host bring-up firmware for an ESP32-S3 DevKitC wired to a daughter through J2
(same wiring as [ir-th-bench](../ir-th-bench/README.md)). On boot it reads the
daughter's EEPROM, validates the image, loads the driver's WAMR AOT module,
links the `babel_v1` host API and prints measurements over serial.

```
babel-host: ESP32-S3 + WAMR AOT, babel_v1
daughter: IR thermometer (MLX90614, TO-39) (babel.ir.mlx90614), driver 0.1.0
  image 4004 bytes, AOT module 2980 bytes, I2C 100000 Hz, period 500 ms
[driver] MLX90614 ready
driver started
babel: ready
object_temperature   19.89 degC   ambient_temperature   19.19 degC
```

Image format and manifest: [board-contract-v0.md](../../board-contract-v0.md)
(format 3). Why AOT only: [runtime-decision.md](../../runtime-decision.md).

## What it checks before running anything

1. Header: magic, format 3, API 1, lengths, reserved bytes zero.
2. SHA-256 over header, manifest and module.
3. Manifest: `wamr-aot`, `aot_target` `xtensa-esp32s3`, `wamr_version` equal
   to the host's WAMR, API major 1, capabilities, I2C addresses, channels.
4. Module: imports are only `babel_v1` functions with matching signatures;
   exports `babel_driver_start/poll/stop` are `() -> i32`.

A blank header means provisioning mode; anything else that fails is reported
and never executed. The driver's I2C transfers can only reach the addresses
its manifest declares.

## Serial commands

`firmware/tools/babel_prog.py` drives these; they can also be typed.

| Command | Effect |
| --- | --- |
| `INFO` | Describe the image and whether the driver runs |
| `TRACE` | Reload the driver, narrating every step (see above) |
| `ERASE` | Invalidate the header page (provisioning mode) |
| `PROG <len> <sha256>` | Receive an image in 256-byte chunks, validate it in RAM, program it (header invalidated first, payload written and verified, header written last, WP released only while writing), then load and start it |

## Watching it load: `babel_trace.py`

```sh
tools/babel_trace.py              # add --samples N for more data lines
```

Resets the board, sends `TRACE`, and prints the reload step by step:

1. Read the daughter EEPROM: header page hex dump, lengths, read time.
2. Verify the image: SHA-256 computed and stored.
3. Parse the manifest: board, WAMR target/version match, I2C address, channels.
4. Load the AOT module into WAMR (about 1.5 ms).
5. Link each import to its `babel_v1` native, with its signature.
6. Instantiate and find the three exports.
7. Start the driver, showing its I2C traffic.
8. Run: the first two polls with every I2C transfer and `submit` call, then
   plain measurement lines.

## Toolchain

All beside the ESP-IDF checkout in `~/projects` (see the ir-th-bench README
for ESP-IDF itself):

| Tool | Where | Notes |
| --- | --- | --- |
| WAMR 2.4.6 | `~/projects/wamr` | `git clone -b WAMR-2.4.6`; override with `WAMR_PATH` |
| wasi-sdk 34 | `~/projects/wasi-sdk-34.0-x86_64-linux` | Release tarball |
| wamrc | `~/projects/wamr/wamr-compiler/build/wamrc` | Built against Espressif's Xtensa LLVM |

Building wamrc (once, about 30 minutes):

```sh
cd ~/projects/wamr
python3 -m venv .venv && .venv/bin/pip install ninja requests
export PATH=$PWD/.venv/bin:$PATH
cd wamr-compiler
python ../build-scripts/build_llvm.py --platform xtensa
#   if it stops on "Unable to find the program ccache", rerun the printed
#   cmake command in core/deps/llvm/build with -DLLVM_CCACHE_BUILD:BOOL=OFF,
#   then: cmake --build . --target package
mkdir -p build && cd build && cmake .. -G Ninja && ninja
```

## Build and run

```sh
get_idf
cd firmware/babel-host
idf.py build && idf.py -p /dev/ttyACM0 flash

cd ..
drivers/build.sh mlx90614                                  # C -> wasm -> AOT -> image.bin
tools/babel_prog.py drivers/mlx90614/build/image.bin       # program and watch
tools/babel_prog.py                                        # reset and watch
tools/babel_prog.py --erase                                # back to provisioning mode
```

## Tested on the bench (2026-11-24)

- Blank EEPROM: provisioning mode.
- Program the MLX90614 image (4,004 bytes, about 1 s): driver starts and
  reports object and ambient temperature every 500 ms.
- Image with one corrupted module byte: rejected (SHA-256) before any write;
  the previous driver keeps running.
- Image whose manifest says WAMR 2.4.5: rejected before any write.
- Erase, reset (provisioning mode), reprogram: driver runs again.

Not done yet: AOT execution limits (a looping driver hangs the host thread),
fault-injection tests, hot-swap, BLE and display.
