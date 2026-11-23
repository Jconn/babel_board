# IR TH daughter bench test (ESP-IDF)

Bring-up firmware for the [IR TH daughter](../../hardware/ir-th-daughter/README.md)
wired to an ESP32-S3-DevKitC-1 through J2. It scans the I2C bus, reads the first
16 bytes of the EEPROM (read-only), then prints the MLX90614 ambient and object
temperatures twice a second with PEC checking.

## Wiring (power off)

The GPIOs match the radio's map (`hardware/radio/gpio-map.csv`), with the two
buses kept separate as on the radio, so this code carries over.

| J2 pin | Signal | DevKitC |
| --- | --- | --- |
| 1 | GND | GND |
| 2 | VDD | 3V3 (never 5V) |
| 3 | sensor SCL | GPIO7 |
| 4 | sensor SDA | GPIO8 |
| 5 | EEPROM SCL | GPIO4 |
| 6 | EEPROM SDA | GPIO5 |
| 7 | EEPROM WP | GPIO6 (driven high: write-protected) |
| 8 | GND | spare |

R2-R5 must be fitted on the daughter; the firmware leaves the ESP32 pull-ups off.

## Toolchain (once)

Requires ESP-IDF v5.3 or newer (the `esp_driver_i2c` component).

```sh
sudo apt install git wget flex bison gperf python3 python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0
git clone -b v5.5 --recursive https://github.com/espressif/esp-idf.git ~/projects/esp-idf
export IDF_TOOLS_PATH=~/projects/esp-idf-tools   # keep the toolchain beside the repo
~/projects/esp-idf/install.sh esp32s3
sudo usermod -aG dialout $USER   # serial port access; log out and back in
```

## Build, flash, monitor

Plug the USB cable into the DevKitC port labelled **UART**.

```sh
export IDF_TOOLS_PATH=~/projects/esp-idf-tools
. ~/projects/esp-idf/export.sh   # every new shell
cd firmware/ir-th-bench
idf.py set-target esp32s3        # first time only
idf.py -p /dev/ttyUSB0 flash monitor
```

Exit the monitor with `Ctrl+]`. If `/dev/ttyUSB0` is missing, check
`ls /dev/ttyUSB* /dev/ttyACM*`.

Expected output: `0x5a` on the sensor bus and `0x50` on the NVM bus, sixteen
`ff` bytes from a blank EEPROM, then a temperature line every 0.5 s. The
object temperature should rise when a finger is held in front of the can.
