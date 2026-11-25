#include "nvm.h"

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "pins.h"

#define EEPROM_ADDR    0x50
#define WRITE_DEADLINE 20000  // us; the 24LC256 write cycle is 5 ms max
#define READ_CHUNK     256

static i2c_master_dev_handle_t eeprom;

esp_err_t nvm_init(void)
{
    gpio_set_level(PIN_NVM_WP, 1);
    gpio_set_direction(PIN_NVM_WP, GPIO_MODE_OUTPUT);

    i2c_master_bus_config_t bus_cfg = {
        .i2c_port = -1,
        .sda_io_num = PIN_NVM_SDA,
        .scl_io_num = PIN_NVM_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,
    };
    i2c_master_bus_handle_t bus;
    esp_err_t err = i2c_new_master_bus(&bus_cfg, &bus);
    if (err != ESP_OK) {
        return err;
    }
    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = EEPROM_ADDR,
        .scl_speed_hz = 100000,
    };
    return i2c_master_bus_add_device(bus, &dev_cfg, &eeprom);
}

esp_err_t nvm_read(uint16_t addr, void *out, size_t len)
{
    uint8_t *p = out;
    while (len > 0) {
        size_t n = len < READ_CHUNK ? len : READ_CHUNK;
        uint8_t a[2] = { addr >> 8, addr & 0xff };
        esp_err_t err = i2c_master_transmit_receive(eeprom, a, sizeof a, p, n, 100);
        if (err != ESP_OK) {
            return err;
        }
        addr += n;
        p += n;
        len -= n;
    }
    return ESP_OK;
}

// One write inside a single page, then ACK-poll until the write cycle ends.
static esp_err_t page_write(uint16_t addr, const uint8_t *data, size_t len)
{
    uint8_t buf[2 + NVM_PAGE_SIZE] = { addr >> 8, addr & 0xff };
    memcpy(buf + 2, data, len);
    esp_err_t err = i2c_master_transmit(eeprom, buf, 2 + len, 100);
    if (err != ESP_OK) {
        return err;
    }
    // A busy chip NACKs; that is the poll working, so keep the driver quiet.
    esp_log_level_t old = esp_log_level_get("i2c.master");
    esp_log_level_set("i2c.master", ESP_LOG_NONE);
    uint8_t dummy;
    int64_t t0 = esp_timer_get_time();
    while ((err = i2c_master_transmit_receive(eeprom, buf, 2, &dummy, 1, 10)) != ESP_OK
           && esp_timer_get_time() - t0 < WRITE_DEADLINE) {
    }
    esp_log_level_set("i2c.master", old);
    return err == ESP_OK ? ESP_OK : ESP_ERR_TIMEOUT;
}

// Writes [addr, addr + len) split at page boundaries, then reads it back.
static esp_err_t write_verified(uint16_t addr, const uint8_t *data, size_t len)
{
    for (size_t off = 0; off < len;) {
        uint16_t a = addr + off;
        size_t n = NVM_PAGE_SIZE - (a % NVM_PAGE_SIZE);
        if (n > len - off) {
            n = len - off;
        }
        esp_err_t err = page_write(a, data + off, n);
        if (err != ESP_OK) {
            return err;
        }
        off += n;
    }
    uint8_t chk[READ_CHUNK];
    for (size_t off = 0; off < len; off += READ_CHUNK) {
        size_t n = len - off < READ_CHUNK ? len - off : READ_CHUNK;
        esp_err_t err = nvm_read(addr + off, chk, n);
        if (err != ESP_OK) {
            return err;
        }
        if (memcmp(chk, data + off, n) != 0) {
            return ESP_ERR_INVALID_CRC;
        }
    }
    return ESP_OK;
}

static void set_wp(int level)
{
    gpio_set_level(PIN_NVM_WP, level);
    vTaskDelay(pdMS_TO_TICKS(1));
}

esp_err_t nvm_invalidate(void)
{
    uint8_t blank[NVM_PAGE_SIZE];
    memset(blank, 0xff, sizeof blank);
    set_wp(0);
    esp_err_t err = write_verified(0, blank, sizeof blank);
    set_wp(1);
    return err;
}

esp_err_t nvm_program(const uint8_t *image, size_t len, const char **why)
{
    if (len < NVM_PAGE_SIZE || len > NVM_SIZE) {
        *why = "image size";
        return ESP_ERR_INVALID_SIZE;
    }
    esp_err_t err = nvm_invalidate();
    if (err != ESP_OK) {
        *why = "invalidate header";
        return err;
    }
    set_wp(0);
    err = write_verified(NVM_PAGE_SIZE, image + NVM_PAGE_SIZE, len - NVM_PAGE_SIZE);
    if (err != ESP_OK) {
        *why = "write/verify payload";
    } else if ((err = write_verified(0, image, NVM_PAGE_SIZE)) != ESP_OK) {
        *why = "write/verify header";
    }
    set_wp(1);
    return err;
}
