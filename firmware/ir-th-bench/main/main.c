// Bench bring-up for the IR TH daughter (MLX90614 + 24LC256) through J2.
// J2 3+5 (SCL) -> GPIO9, J2 4+6 (SDA) -> GPIO8, J2 2 -> 3V3, J2 1 -> GND.
// Pull-ups are R2-R5 on the daughter; the ESP32's internal ones stay off.

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c_master.h"
#include "esp_log.h"

#define SDA_GPIO    8
#define SCL_GPIO    9
#define BUS_HZ      100000  // MLX90614 is SMBus: 100 kHz max
#define MLX_ADDR    0x5A
#define EEPROM_ADDR 0x50

#define MLX_RAM_TA   0x06  // ambient (die) temperature
#define MLX_RAM_TOBJ 0x07  // object temperature

static const char *TAG = "ir-th-bench";

// SMBus PEC: CRC-8, polynomial x^8 + x^2 + x + 1, initial value 0.
static uint8_t crc8(const uint8_t *d, size_t n)
{
    uint8_t c = 0;
    for (size_t i = 0; i < n; i++) {
        c ^= d[i];
        for (int b = 0; b < 8; b++) {
            c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1);
        }
    }
    return c;
}

// SMBus "read word": command byte, repeated start, LSB, MSB, PEC.
static esp_err_t mlx_read(i2c_master_dev_handle_t dev, uint8_t cmd, uint16_t *out)
{
    uint8_t rx[3];
    esp_err_t err = i2c_master_transmit_receive(dev, &cmd, 1, rx, sizeof rx, 100);
    if (err != ESP_OK) {
        return err;
    }
    uint8_t frame[5] = { MLX_ADDR << 1, cmd, (MLX_ADDR << 1) | 1, rx[0], rx[1] };
    if (crc8(frame, sizeof frame) != rx[2]) {
        return ESP_ERR_INVALID_CRC;
    }
    *out = rx[0] | (rx[1] << 8);
    return ESP_OK;
}

static void print_temp(const char *name, esp_err_t err, uint16_t raw)
{
    if (err != ESP_OK) {
        printf("%s: %s  ", name, esp_err_to_name(err));
    } else if (raw & 0x8000) {
        printf("%s: sensor error flag (0x%04x)  ", name, raw);
    } else {
        printf("%s: %6.2f C  ", name, raw * 0.02 - 273.15);
    }
}

void app_main(void)
{
    i2c_master_bus_config_t bus_cfg = {
        .i2c_port = -1,
        .sda_io_num = SDA_GPIO,
        .scl_io_num = SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,
    };
    i2c_master_bus_handle_t bus;
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus));

    vTaskDelay(pdMS_TO_TICKS(300));  // MLX90614 needs ~250 ms after power-up

    printf("\nI2C scan (SDA=GPIO%d, SCL=GPIO%d):\n", SDA_GPIO, SCL_GPIO);
    int found = 0;
    for (uint16_t a = 0x08; a < 0x78; a++) {
        if (i2c_master_probe(bus, a, 50) == ESP_OK) {
            printf("  0x%02x%s\n", a,
                   a == MLX_ADDR ? "  MLX90614" : a == EEPROM_ADDR ? "  24LC256" : "");
            found++;
        }
    }
    printf("%d device(s); expect 0x50 and 0x5a\n\n", found);

    i2c_device_config_t mlx_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = MLX_ADDR,
        .scl_speed_hz = BUS_HZ,
    };
    i2c_device_config_t eeprom_cfg = mlx_cfg;
    eeprom_cfg.device_address = EEPROM_ADDR;
    i2c_master_dev_handle_t mlx, eeprom;
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &mlx_cfg, &mlx));
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &eeprom_cfg, &eeprom));

    // Read-only EEPROM check: a blank 24LC256 reads 0xff.
    uint8_t addr[2] = { 0x00, 0x00 };
    uint8_t data[16];
    esp_err_t err = i2c_master_transmit_receive(eeprom, addr, sizeof addr, data, sizeof data, 100);
    if (err == ESP_OK) {
        printf("EEPROM 0x0000:");
        for (int i = 0; i < sizeof data; i++) {
            printf(" %02x", data[i]);
        }
        printf("\n\n");
    } else {
        ESP_LOGE(TAG, "EEPROM read failed: %s", esp_err_to_name(err));
    }

    while (1) {
        uint16_t ta = 0, to = 0;
        esp_err_t ea = mlx_read(mlx, MLX_RAM_TA, &ta);
        esp_err_t eo = mlx_read(mlx, MLX_RAM_TOBJ, &to);
        print_temp("ambient", ea, ta);
        print_temp("object", eo, to);
        printf("\n");
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
