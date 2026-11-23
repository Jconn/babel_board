#!/usr/bin/env python3
"""Print the bench firmware's output. Standard library only; no ESP-IDF needed.

    ./watch.py [port]          default port /dev/ttyACM0; Ctrl+C to quit

Resets the board on start so the line check and bus scans are shown too.
"""
import fcntl
import os
import select
import struct
import sys
import termios
import time

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"

try:
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
except OSError as e:
    sys.exit(f"{port}: {e.strerror}. Is the board plugged into the UART port?")

# 115200 8N1, raw.
attrs = termios.tcgetattr(fd)
attrs[0] = 0                                                    # iflag
attrs[1] = 0                                                    # oflag
attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL        # cflag
attrs[3] = 0                                                    # lflag
attrs[4] = attrs[5] = termios.B115200                          # ispeed, ospeed
termios.tcsetattr(fd, termios.TCSANOW, attrs)

# Reset: RTS drives EN low, DTR (IO0) stays released so it boots normally.
def lines(op, bits):
    fcntl.ioctl(fd, op, struct.pack("I", bits))

lines(termios.TIOCMBIC, termios.TIOCM_DTR)
lines(termios.TIOCMBIS, termios.TIOCM_RTS)
time.sleep(0.1)
lines(termios.TIOCMBIC, termios.TIOCM_RTS)
termios.tcflush(fd, termios.TCIFLUSH)  # drop output from before the reset

print(f"Watching {port} (Ctrl+C to quit)\n")
buf = b""
try:
    while True:
        if select.select([fd], [], [], 1.0)[0]:
            buf += os.read(fd, 4096)
            *done, buf = buf.split(b"\n")
            for line in done:
                text = line.decode(errors="replace").rstrip("\r")
                # Skip the ROM/boot chatter; keep the bench output and errors.
                if text and not text.startswith(("I (", "ESP-ROM", "Build:", "rst:", "boot:",
                                                 "SPIWP", "mode:", "load:", "entry ")) \
                        and "spi_flash: Detected size" not in text \
                        and "check pull-up resistances" not in text:  # known, harmless
                    print(text, flush=True)
except KeyboardInterrupt:
    print()
finally:
    os.close(fd)
