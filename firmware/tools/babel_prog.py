#!/usr/bin/env python3
"""Program a daughter image through babel-host over USB serial, then watch.

    babel_prog.py image.bin        program, then show the host's output
    babel_prog.py --erase          invalidate the image (provisioning mode)
    babel_prog.py --info           describe the current image
    babel_prog.py                  just reset and watch

Options: --port /dev/ttyACM0, --seconds N (stop watching after N s; default
runs until Ctrl+C). Standard library only.
"""
import argparse
import fcntl
import hashlib
import os
import select
import struct
import sys
import termios
import time

CHUNK = 256


class Port:
    def __init__(self, path):
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
        except OSError as e:
            sys.exit(f"{path}: {e.strerror}. Is the board plugged into the UART port?")
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = attrs[1] = attrs[3] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[4] = attrs[5] = termios.B115200
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        self.buf = b""

    def _lines(self, op, bits):
        fcntl.ioctl(self.fd, op, struct.pack("I", bits))

    def reset(self):
        # RTS drives EN low; DTR (IO0) stays released so the board boots normally.
        self._lines(termios.TIOCMBIC, termios.TIOCM_DTR)
        self._lines(termios.TIOCMBIS, termios.TIOCM_RTS)
        time.sleep(0.1)
        self._lines(termios.TIOCMBIC, termios.TIOCM_RTS)
        termios.tcflush(self.fd, termios.TCIFLUSH)
        self.buf = b""

    def write(self, data):
        os.write(self.fd, data)
        termios.tcdrain(self.fd)

    def readline(self, timeout):
        """One line without its newline, or None on timeout."""
        end = time.time() + timeout
        while b"\n" not in self.buf:
            left = end - time.time()
            if left <= 0 or not select.select([self.fd], [], [], left)[0]:
                return None
            self.buf += os.read(self.fd, 4096)
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode(errors="replace").rstrip("\r")


def show(line):
    # Skip ROM/boot chatter and known-harmless warnings.
    if line and not line.startswith(("I (", "ESP-ROM", "Build:", "rst:", "boot:", "SPIWP", "mode:",
                                     "load:", "entry ")) \
            and "spi_flash: Detected size" not in line and "check pull-up resistances" not in line:
        print(line, flush=True)


def expect(port, prefix, timeout):
    """Print lines until one starts with prefix; return it. Exit on FAIL or timeout."""
    while True:
        line = port.readline(timeout)
        if line is None:
            sys.exit(f"timed out waiting for '{prefix}'")
        show(line)
        if line.startswith(prefix):
            return line
        if " FAIL" in line[:12]:
            sys.exit(1)


def program(port, image):
    digest = hashlib.sha256(image).hexdigest()
    print(f"> PROG {len(image)} bytes, sha256 {digest[:16]}...")
    port.write(f"PROG {len(image)} {digest}\n".encode())
    expect(port, "PROG READY", 5)
    for off in range(0, len(image), CHUNK):
        chunk = image[off:off + CHUNK]
        port.write(chunk)
        while True:
            line = port.readline(5)
            if line is None:
                sys.exit(f"no ACK after byte {off + len(chunk)}")
            if line.startswith("PROG ACK"):
                break
            show(line)
            if line.startswith("PROG FAIL"):
                sys.exit(1)
        print(f"\r  sent {off + len(chunk)}/{len(image)}", end="", flush=True)
    print()
    expect(port, "PROG OK", 30)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?")
    ap.add_argument("--erase", action="store_true")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--seconds", type=float)
    args = ap.parse_args()

    image = None
    if args.image:
        with open(args.image, "rb") as f:
            image = f.read()

    port = Port(args.port)
    port.reset()
    expect(port, "babel: ready", 10)
    if image is not None:
        program(port, image)
    elif args.erase:
        port.write(b"ERASE\n")
        expect(port, "ERASE", 10)
    elif args.info:
        port.write(b"INFO\n")
        expect(port, "INFO", 5)

    end = time.time() + args.seconds if args.seconds else None
    try:
        while end is None or time.time() < end:
            line = port.readline(0.5 if end is None else max(0.0, min(0.5, end - time.time())))
            if line is not None:
                show(line)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
