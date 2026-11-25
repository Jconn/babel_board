#!/bin/sh
# Build a daughter driver: C -> wasm32 -> WAMR AOT (ESP32-S3) -> EEPROM image.
#
#   drivers/build.sh mlx90614        writes drivers/mlx90614/build/image.bin
#
# Toolchain locations (override with environment variables):
#   WASI_SDK  wasi-sdk 34   (default ~/projects/wasi-sdk-34.0-x86_64-linux)
#   WAMRC     wamrc 2.4.6 built with Xtensa LLVM (default ~/projects/wamr/wamr-compiler/build/wamrc)
set -eu

here=$(cd "$(dirname "$0")" && pwd)
name=${1:?usage: build.sh <driver dir>}
src="$here/$name"
out="$src/build"
WASI_SDK=${WASI_SDK:-$HOME/projects/wasi-sdk-34.0-x86_64-linux}
WAMRC=${WAMRC:-$HOME/projects/wamr/wamr-compiler/build/wamrc}

mkdir -p "$out"

# No libc, no entry point, no start section: the host calls the three exports.
# One 64 KiB page of linear memory, 4 KiB of it guest stack.
"$WASI_SDK/bin/clang" --target=wasm32 -O2 -nostdlib -Wall -Werror \
    -I"$here/include" \
    -Wl,--no-entry -Wl,--strip-all -Wl,-z,stack-size=4096 \
    -Wl,--initial-memory=65536 -Wl,--max-memory=65536 \
    -o "$out/driver.wasm" "$src"/*.c

# Xtensa ESP32-S3; the AOT file is tied to this target and this WAMR version.
"$WAMRC" --target=xtensa --cpu=esp32s3 -o "$out/driver.aot" "$out/driver.wasm"

python3 "$here/../tools/babel_image.py" pack "$src/manifest.json" "$out/driver.aot" -o "$out/image.bin"
echo "wasm $(wc -c < "$out/driver.wasm") bytes, aot $(wc -c < "$out/driver.aot") bytes"
