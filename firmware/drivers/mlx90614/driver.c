// MLX90614 driver for the IR TH daughter, built as wasm32 then AOT for the host.
// Reads RAM 0x06 (ambient) and 0x07 (object) with SMBus PEC checking.
// Channels match manifest.json: 0 object_temperature, 1 ambient_temperature.

#include "babel_v1.h"

#define MLX_ADDR     0x5A
#define MLX_RAM_TA   0x06
#define MLX_RAM_TOBJ 0x07

#define LOG(s) babel_log(s, sizeof(s) - 1)

// SMBus PEC: CRC-8, polynomial x^8 + x^2 + x + 1, initial value 0.
static uint8_t crc8(const uint8_t *d, int n)
{
    uint8_t c = 0;
    for (int i = 0; i < n; i++) {
        c ^= d[i];
        for (int b = 0; b < 8; b++) {
            c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1);
        }
    }
    return c;
}

// SMBus read word: command, repeated start, LSB, MSB, PEC. Stores the raw
// register (0.02 K per count) in *raw; returns 0 or a negative error.
static int32_t read_ram(uint8_t cmd, uint16_t *raw)
{
    uint8_t rx[3];
    int32_t err = babel_i2c_transfer(MLX_ADDR, &cmd, 1, rx, sizeof rx);
    if (err != BABEL_OK) {
        return err;
    }
    uint8_t frame[5] = { MLX_ADDR << 1, cmd, (MLX_ADDR << 1) | 1, rx[0], rx[1] };
    if (crc8(frame, sizeof frame) != rx[2]) {
        LOG("PEC mismatch");
        return -10;
    }
    *raw = (uint16_t)(rx[0] | (rx[1] << 8));
    if (*raw & 0x8000) {
        LOG("sensor error flag");
        return -11;
    }
    return BABEL_OK;
}

static float to_celsius(uint16_t raw)
{
    return raw * 0.02f - 273.15f;
}

BABEL_EXPORT(babel_driver_start)
int32_t babel_driver_start(void)
{
    uint16_t raw;
    int32_t err = read_ram(MLX_RAM_TA, &raw);
    if (err != BABEL_OK) {
        LOG("MLX90614 not responding");
        return err;
    }
    LOG("MLX90614 ready");
    return BABEL_OK;
}

BABEL_EXPORT(babel_driver_poll)
int32_t babel_driver_poll(void)
{
    uint16_t ta, to;
    int32_t err = read_ram(MLX_RAM_TA, &ta);
    if (err == BABEL_OK) {
        err = read_ram(MLX_RAM_TOBJ, &to);
    }
    if (err != BABEL_OK) {
        return err;
    }
    babel_submit(0, to_celsius(to));
    babel_submit(1, to_celsius(ta));
    return BABEL_OK;
}

BABEL_EXPORT(babel_driver_stop)
int32_t babel_driver_stop(void)
{
    return BABEL_OK;  // nothing to undo: the sensor needs no shutdown
}
