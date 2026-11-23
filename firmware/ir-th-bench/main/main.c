// Bench bring-up for the IR TH daughter (MLX90614 + 24LC256) through J2.
// GPIOs match the radio (hardware/radio/gpio-map.csv) so the code carries over:
// sensor bus J2.3 SCL -> GPIO7, J2.4 SDA -> GPIO8; NVM bus J2.5 SCL -> GPIO4,
// J2.6 SDA -> GPIO5, J2.7 WP -> GPIO6; J2.2 -> 3V3, J2.1 -> GND.
// Pull-ups are R2-R5 on the daughter; the ESP32's internal ones stay off.

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_log.h"

#define SENSOR_SCL_GPIO 7
#define SENSOR_SDA_GPIO 8
#define NVM_SCL_GPIO    4
#define NVM_SDA_GPIO    5
#define NVM_WP_GPIO     6  // high = write-protected (R1 also pulls it high)
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

static i2c_master_bus_handle_t new_bus(int sda, int scl)
{
    i2c_master_bus_config_t cfg = {
        .i2c_port = -1,
        .sda_io_num = sda,
        .scl_io_num = scl,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,
    };
    i2c_master_bus_handle_t bus;
    ESP_ERROR_CHECK(i2c_new_master_bus(&cfg, &bus));
    return bus;
}

static void scan(i2c_master_bus_handle_t bus, const char *name, uint16_t expect)
{
    printf("%s bus scan:", name);
    int found = 0;
    for (uint16_t a = 0x08; a < 0x78; a++) {
        if (i2c_master_probe(bus, a, 50) == ESP_OK) {
            printf(" 0x%02x", a);
            found++;
        }
    }
    printf("%s (expect 0x%02x)\n", found ? "" : " nothing", expect);
}

// Before the buses start: R2-R5 (4.7k) beat the ESP32's ~45k internal pulls,
// so a powered, wired line reads high with either internal pull.
static void line_check(void)
{
    static const struct { int gpio; const char *name; } lines[] = {
        { SENSOR_SCL_GPIO, "J2.3 sensor SCL" }, { SENSOR_SDA_GPIO, "J2.4 sensor SDA" },
        { NVM_SCL_GPIO, "J2.5 NVM SCL" },       { NVM_SDA_GPIO, "J2.6 NVM SDA" },
        { NVM_WP_GPIO, "J2.7 NVM WP" },
    };
    printf("\nLine check (pulled-down read, pulled-up read):\n");
    for (int i = 0; i < sizeof lines / sizeof lines[0]; i++) {
        int g = lines[i].gpio;
        gpio_reset_pin(g);
        gpio_set_direction(g, GPIO_MODE_INPUT);
        gpio_set_pull_mode(g, GPIO_PULLDOWN_ONLY);
        vTaskDelay(pdMS_TO_TICKS(5));
        int lo = gpio_get_level(g);
        gpio_set_pull_mode(g, GPIO_PULLUP_ONLY);
        vTaskDelay(pdMS_TO_TICKS(5));
        int hi = gpio_get_level(g);
        gpio_set_pull_mode(g, GPIO_FLOATING);
        printf("  GPIO%-2d %-16s %d %d  %s\n", g, lines[i].name, lo, hi,
               lo && hi ? "pulled high (ok)" : !lo && !hi ? "held LOW" : "floating (no pull-up reached)");
    }
}

void app_main(void)
{
    line_check();

    gpio_set_level(NVM_WP_GPIO, 1);
    gpio_set_direction(NVM_WP_GPIO, GPIO_MODE_OUTPUT);

    i2c_master_bus_handle_t sensor_bus = new_bus(SENSOR_SDA_GPIO, SENSOR_SCL_GPIO);
    i2c_master_bus_handle_t nvm_bus = new_bus(NVM_SDA_GPIO, NVM_SCL_GPIO);

    vTaskDelay(pdMS_TO_TICKS(300));  // MLX90614 needs ~250 ms after power-up

    printf("\n");
    scan(sensor_bus, "sensor", MLX_ADDR);
    scan(nvm_bus, "NVM", EEPROM_ADDR);
    printf("\n");

    i2c_device_config_t mlx_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = MLX_ADDR,
        .scl_speed_hz = BUS_HZ,
    };
    i2c_device_config_t eeprom_cfg = mlx_cfg;
    eeprom_cfg.device_address = EEPROM_ADDR;
    i2c_master_dev_handle_t mlx, eeprom;
    ESP_ERROR_CHECK(i2c_master_bus_add_device(sensor_bus, &mlx_cfg, &mlx));
    ESP_ERROR_CHECK(i2c_master_bus_add_device(nvm_bus, &eeprom_cfg, &eeprom));

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
