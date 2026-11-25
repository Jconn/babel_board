# EEPROM write/read test (ESP-IDF)

Checks the IR TH daughter's 24LC256 and its write-protect line, using the
same J2 wiring as [ir-th-bench](../ir-th-bench/README.md) (NVM bus on GPIO4/5,
WP on GPIO6). It only touches the last 64-byte page (0x7fc0) and leaves it
erased.

1. WP high: write a pattern; the page must not change.
2. WP low: write the pattern ("Babel EEPROM test" plus filler); it must read back.
3. WP low: write 0xff back, then set WP high again.

```sh
get_idf
cd firmware/eeprom-test
idf.py -p /dev/ttyACM0 flash
../ir-th-bench/watch.py
```

It runs once per reset, so reflash `ir-th-bench` afterwards for the normal
bench readout. First board, 2026-11-24: all three passed; the write cycle took
4.6 ms (datasheet maximum 5 ms).
