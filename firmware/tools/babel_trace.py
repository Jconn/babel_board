#!/usr/bin/env python3
"""Show the host loading a daughter driver step by step, then its data.

    babel_trace.py [--samples N] [--port /dev/ttyACM0]

Resets babel-host, sends TRACE, and prints the narrated reload: reading the
daughter EEPROM, verifying the image, parsing the manifest, loading the AOT
module into WAMR, linking babel_v1, starting the driver, then the first polls
with their I2C traffic and N measurement lines (default 6).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from babel_prog import Port, expect, show  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--port", default="/dev/ttyACM0")
    args = ap.parse_args()

    port = Port(args.port)
    port.reset()
    # Swallow the ordinary boot (it loads the driver quietly), then ask for the narrated reload.
    while True:
        line = port.readline(10)
        if line is None:
            sys.exit("babel-host did not report ready; is it flashed?")
        if line.startswith("babel: ready"):
            break
    port.write(b"TRACE\n")
    expect(port, "TRACE", 5)

    samples = 0
    running = False  # measurement lines follow the "== 8. Run" section header
    while samples < args.samples:
        line = port.readline(5)
        if line is None:
            sys.exit("\nno more output from the board")
        show(line)
        if "provisioning mode" in line or line.startswith(("fault", "driver rejected")):
            sys.exit(1)
        if line.startswith("== 8."):
            running = True
        elif running and line and not line.startswith((" ", "==")):
            samples += 1


if __name__ == "__main__":
    main()
