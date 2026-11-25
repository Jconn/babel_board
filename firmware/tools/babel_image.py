#!/usr/bin/env python3
"""Build or inspect a Babel daughter EEPROM image (board-contract-v0, format 3).

    babel_image.py pack manifest.json driver.aot -o image.bin
    babel_image.py show image.bin

The image is the EEPROM's contents from address 0: a 64-byte header page,
the JSON manifest padded with 0xff to 0x400, then the module (WAMR AOT for
format 3). Trailing padding is not stored; the EEPROM beyond it is ignored.
"""
import argparse
import hashlib
import json
import struct
import sys

MAGIC = b"BABELW01"
FORMAT_VERSION = 3          # 3 = module is a WAMR AOT file (2 was portable .wasm)
API_VERSION = 1
HEADER_SIZE = 64
MANIFEST_ADDR, MANIFEST_MAX = 0x0040, 960
MODULE_ADDR, MODULE_MAX = 0x0400, 28672
AOT_MAGIC = b"\x00aot"
HEAD = struct.Struct("<8sHHHHI")  # magic, format, api, manifest len, reserved, module len


def digest(head20, manifest, module):
    return hashlib.sha256(head20 + manifest + module).digest()


def pack(manifest_path, module_path):
    with open(manifest_path, "rb") as f:
        manifest_obj = json.load(f)
    # Compact, stable encoding: what the host parses is exactly what was hashed.
    manifest = json.dumps(manifest_obj, separators=(",", ":"), ensure_ascii=False).encode()
    with open(module_path, "rb") as f:
        module = f.read()

    if manifest_obj.get("babel_api_major") != API_VERSION:
        sys.exit(f"manifest babel_api_major must be {API_VERSION}")
    if manifest_obj.get("runtime") != "wamr-aot":
        sys.exit('format 3 needs manifest "runtime": "wamr-aot"')
    if not module.startswith(AOT_MAGIC):
        sys.exit(f"{module_path} is not a WAMR AOT file (no \\0aot magic)")
    if not 1 <= len(manifest) <= MANIFEST_MAX:
        sys.exit(f"manifest is {len(manifest)} bytes; limit {MANIFEST_MAX}")
    if not 8 <= len(module) <= MODULE_MAX:
        sys.exit(f"module is {len(module)} bytes; limit {MODULE_MAX} (never truncated)")

    head20 = HEAD.pack(MAGIC, FORMAT_VERSION, API_VERSION, len(manifest), 0, len(module))
    header = head20 + digest(head20, manifest, module) + bytes(12)
    assert len(header) == HEADER_SIZE
    pad = b"\xff" * (MODULE_ADDR - MANIFEST_ADDR - len(manifest))
    return header + manifest + pad + module


def show(image):
    if len(image) < HEADER_SIZE:
        sys.exit("image shorter than a header")
    magic, fmt, api, mlen, rsv, modlen = HEAD.unpack_from(image)
    want = image[20:52]
    manifest = image[MANIFEST_ADDR:MANIFEST_ADDR + mlen]
    module = image[MODULE_ADDR:MODULE_ADDR + modlen]
    ok = (magic == MAGIC and rsv == 0 and image[52:64] == bytes(12)
          and digest(image[:20], manifest, module) == want)
    print(f"magic {magic!r}  format {fmt}  api {api}")
    print(f"manifest {mlen} bytes at 0x{MANIFEST_ADDR:04x}, module {modlen} bytes at 0x{MODULE_ADDR:04x}")
    print(f"image {len(image)} bytes, {len(image) * 100 // 32768}% of the 32 KiB EEPROM")
    print(f"sha256 {want.hex()}  {'OK' if ok else 'MISMATCH'}")
    print(manifest.decode(errors="replace"))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("manifest")
    p.add_argument("module")
    p.add_argument("-o", "--output", required=True)
    s = sub.add_parser("show")
    s.add_argument("image")
    args = ap.parse_args()

    if args.cmd == "pack":
        image = pack(args.manifest, args.module)
        with open(args.output, "wb") as f:
            f.write(image)
        show(image)
    else:
        with open(args.image, "rb") as f:
            sys.exit(0 if show(f.read()) else 1)


if __name__ == "__main__":
    main()
