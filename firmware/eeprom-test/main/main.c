// EEPROM write/read test for the IR TH daughter's 24LC256 through J2.
// Same wiring as ir-th-bench: NVM bus J2.5 SCL -> GPIO4, J2.6 SDA -> GPIO5,
// J2.7 WP -> GPIO6. Uses only the last 64-byte page and leaves it erased (0xff).
//
//   1. WP high: write a pattern; the page must stay unchanged (protection works).
//   2. WP low:  write the pattern; it must read back exactly (writes work).
//   3. WP low:  write 0xff back; then WP high again.

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "esp_timer.h"

#define NVM_SCL_GPIO 4
#define NVM_SDA_GPIO 5
#define NVM_WP_GPIO  6  // high = write-protected (R1 also pulls it high)
#define BUS_HZ       100000
#define EEPROM_ADDR  0x50

#define PAGE_SIZE    64
#define TEST_ADDR    0x7fc0  // last page of 32 KiB

static i2c_master_dev_handle_t eeprom;

static void hexdump(const char *label, const uint8_t *d)
{
    printf("  %s:", label);
    for (int i = 0; i < PAGE_SIZE; i++) {
        printf("%s%02x", i % 16 ? " " : "\n    ", d[i]);
    }
    printf("\n");
}

static esp_err_t page_read(uint8_t *out)
{
    uint8_t addr[2] = { TEST_ADDR >> 8, TEST_ADDR & 0xff };
    return i2c_master_transmit_receive(eeprom, addr, sizeof addr, out, PAGE_SIZE, 100);
}

// Page write, then ACK-poll until the internal write cycle (5 ms max) ends.
// Returns the time the chip spent busy, or -1 on a bus error.
static int page_write(const uint8_t *data)
{
    uint8_t buf[2 + PAGE_SIZE] = { TEST_ADDR >> 8, TEST_ADDR & 0xff };
    memcpy(buf + 2, data, PAGE_SIZE);
    if (i2c_master_transmit(eeprom, buf, sizeof buf, 100) != ESP_OK) {
        return -1;
    }
    int64_t t0 = esp_timer_get_time();
    uint8_t dummy;
    uint8_t addr[2] = { TEST_ADDR >> 8, TEST_ADDR & 0xff };
    while (i2c_master_transmit_receive(eeprom, addr, sizeof addr, &dummy, 1, 10) != ESP_OK) {
        if (esp_timer_get_time() - t0 > 20000) {
            return -1;
        }
    }
    return (int)(esp_timer_get_time() - t0);
}

static void set_wp(int level)
{
    gpio_set_level(NVM_WP_GPIO, level);
    vTaskDelay(pdMS_TO_TICKS(1));
}

static bool step(const char *name, bool pass)
{
    printf("%s  %s\n\n", pass ? "PASS" : "FAIL", name);
    return pass;
}

void app_main(void)
{
    // A busy chip NACKs while it writes; that is the ACK poll working, not an error.
    esp_log_level_set("i2c.master", ESP_LOG_NONE);

    gpio_set_level(NVM_WP_GPIO, 1);
    gpio_set_direction(NVM_WP_GPIO, GPIO_MODE_OUTPUT);

    i2c_master_bus_config_t bus_cfg = {
        .i2c_port = -1,
        .sda_io_num = NVM_SDA_GPIO,
        .scl_io_num = NVM_SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,
    };
    i2c_master_bus_handle_t bus;
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus));
    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = EEPROM_ADDR,
        .scl_speed_hz = BUS_HZ,
    };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &dev_cfg, &eeprom));

    printf("\n=== 24LC256 write/read test, page 0x%04x ===\n\n", TEST_ADDR);

    uint8_t before[PAGE_SIZE], pattern[PAGE_SIZE], blank[PAGE_SIZE], got[PAGE_SIZE];
    const char msg[] = "Babel EEPROM test";
    for (int i = 0; i < PAGE_SIZE; i++) {
        pattern[i] = i < sizeof msg - 1 ? msg[i] : (uint8_t)(i * 37 + 11);
    }
    memset(blank, 0xff, PAGE_SIZE);

    int fails = 0;
    if (page_read(before) != ESP_OK) {
        printf("FAIL  EEPROM does not answer at 0x%02x\n", EEPROM_ADDR);
        return;
    }
    hexdump("page before", before);
    printf("\n");

    printf("1. WP high, write pattern\n");
    set_wp(1);
    int us = page_write(pattern);  // the chip may ACK or NACK; either way nothing is stored
    page_read(got);
    hexdump("read back", got);
    printf("  write cycle %d us (no cycle expected)\n", us);
    fails += !step("write blocked by WP", memcmp(got, before, PAGE_SIZE) == 0);

    printf("2. WP low, write pattern\n");
    set_wp(0);
    us = page_write(pattern);
    page_read(got);
    hexdump("read back", got);
    printf("  text: \"%.*s\", write cycle %d us\n", (int)sizeof msg - 1, got, us);
    fails += !step("pattern written and read back", us >= 0 && memcmp(got, pattern, PAGE_SIZE) == 0);

    printf("3. WP low, erase page to 0xff\n");
    us = page_write(blank);
    page_read(got);
    set_wp(1);
    fails += !step("page restored to 0xff, WP high", us >= 0 && memcmp(got, blank, PAGE_SIZE) == 0);

    printf("=== %s (%d failure%s) ===\n", fails ? "FAILED" : "ALL PASSED", fails, fails == 1 ? "" : "s");
}
