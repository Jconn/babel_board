// Babel host bring-up on an ESP32-S3 DevKitC: loads the daughter's driver
// (WAMR AOT) from its EEPROM and runs it, printing measurements on serial.
//
// Serial commands (one line each, from firmware/tools/babel_prog.py):
//   INFO                    describe the daughter image
//   TRACE                   reload the driver, narrating every step
//   ERASE                   invalidate the header (provisioning mode)
//   PROG <len> <sha256hex>  receive an image in 256-byte chunks, each answered
//                           "PROG ACK <total>"; then program, verify and start it.
// Replies start with the command word, so a script can pick them out of the log.

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "mbedtls/sha256.h"
#include "driver_host.h"
#include "image.h"
#include "nvm.h"
#include "trace.h"

#define CONSOLE_UART  UART_NUM_0
#define CMD_LINE_MAX      96
#define CHUNK         256
#define CHUNK_TIMEOUT 2000  // ms
#define HOST_STACK    16384

bool g_trace;
int g_trace_polls;

static babel_image_t image;
static bool have_image;
static uint32_t period_ms = 500;

static void describe(void)
{
    if (!have_image) {
        return;
    }
    printf("daughter: %s (%s), driver %s\n", image.name, image.board_type, image.driver_version);
    printf("  image %lu bytes, AOT module %lu bytes, I2C %lu Hz, period %lu ms\n",
           (unsigned long)image.image_len, (unsigned long)image.module_len,
           (unsigned long)image.i2c_hz, (unsigned long)image.sample_period_ms);
}

static void unload(void)
{
    if (driver_running()) {
        driver_stop();
    }
    if (have_image) {
        image_free(&image);
        have_image = false;
    }
}

// Discovery: never execute anything that is blank, unreadable or invalid.
static void discover_and_start(void)
{
    char why[96];
    unload();
    switch (image_load(&image, why, sizeof why)) {
    case IMG_BLANK:
        printf("provisioning mode: no driver image on the daughter\n");
        return;
    case IMG_IO:
        printf("no daughter: EEPROM not answering (%s)\n", why);
        return;
    case IMG_INVALID:
        printf("provisioning mode: image invalid, not executed: %s\n", why);
        return;
    case IMG_OK:
        break;
    }
    have_image = true;
    describe();
    period_ms = image.sample_period_ms;
    if (driver_start(&image)) {
        printf("driver started\n");
        SECTION("8. Run: babel_driver_poll() every sample period");
    } else {
        printf("fault: driver did not start\n");
    }
}

static bool read_exact(uint8_t *buf, size_t n, int timeout_ms)
{
    int got = uart_read_bytes(CONSOLE_UART, buf, n, pdMS_TO_TICKS(timeout_ms));
    return got == (int)n;
}

static void cmd_prog(const char *args)
{
    unsigned long len;
    char hex[65];
    if (sscanf(args, "%lu %64s", &len, hex) != 2 || strlen(hex) != 64 || len < 64 || len > NVM_SIZE) {
        printf("PROG FAIL usage: PROG <len 64..%d> <sha256 hex>\n", NVM_SIZE);
        return;
    }
    unload();
    uint8_t *buf = malloc(len);
    if (!buf) {
        printf("PROG FAIL out of memory\n");
        return;
    }
    printf("PROG READY\n");
    for (unsigned long off = 0; off < len; off += CHUNK) {
        size_t n = len - off < CHUNK ? len - off : CHUNK;
        if (!read_exact(buf + off, n, CHUNK_TIMEOUT)) {
            printf("PROG FAIL timeout at byte %lu\n", off);
            goto done;
        }
        printf("PROG ACK %lu\n", off + n);
    }

    uint8_t digest[32];
    char got[65];
    mbedtls_sha256(buf, len, digest, 0);
    for (int i = 0; i < 32; i++) {
        sprintf(got + 2 * i, "%02x", digest[i]);
    }
    if (strcmp(got, hex) != 0) {
        printf("PROG FAIL transfer checksum mismatch\n");
        goto done;
    }

    // Validate before touching the EEPROM; a bad image is never written.
    babel_image_t tmp;
    char why[96];
    if (image_check(buf, len, &tmp, why, sizeof why) != IMG_OK) {
        printf("PROG FAIL image rejected: %s\n", why);
        goto done;
    }
    image_free(&tmp);
    if (tmp.image_len != len) {
        printf("PROG FAIL image length %lu does not match its header (%lu)\n", len,
               (unsigned long)tmp.image_len);
        goto done;
    }

    printf("PROG WRITING %lu bytes (WP released)\n", len);
    int64_t t0 = esp_timer_get_time();
    const char *step = "";
    esp_err_t err = nvm_program(buf, len, &step);
    if (err != ESP_OK) {
        printf("PROG FAIL eeprom %s: %s (WP restored)\n", step, esp_err_to_name(err));
        goto done;
    }
    printf("PROG OK %lu bytes written and verified in %lld ms, WP high\n", len,
           (esp_timer_get_time() - t0) / 1000);
    free(buf);
    buf = NULL;
    discover_and_start();
done:
    free(buf);
}

static void handle(char *line)
{
    if (strncmp(line, "PROG ", 5) == 0) {
        cmd_prog(line + 5);
    } else if (strcmp(line, "ERASE") == 0) {
        unload();
        esp_err_t err = nvm_invalidate();
        printf(err == ESP_OK ? "ERASE OK header invalidated, provisioning mode\n" : "ERASE FAIL %s\n",
               esp_err_to_name(err));
    } else if (strcmp(line, "TRACE") == 0) {
        printf("TRACE reloading the daughter driver step by step\n");
        g_trace = true;
        g_trace_polls = 2;
        discover_and_start();
        g_trace = false;
    } else if (strcmp(line, "INFO") == 0) {
        printf("INFO %s\n", driver_running() ? "driver running" : "no driver running");
        describe();
    } else if (line[0]) {
        printf("? unknown command: %s\n", line);
    }
}

// WAMR on ESP-IDF calls pthread_self(), so everything that touches the
// runtime runs on a pthread rather than the main task.
static void *host_main(void *arg)
{
    if (nvm_init() != ESP_OK || !driver_host_init()) {
        printf("fault: host init failed\n");
        return NULL;
    }
    discover_and_start();
    printf("babel: ready\n");

    char line[CMD_LINE_MAX];
    int len = 0;
    int64_t next = esp_timer_get_time();
    for (;;) {
        int64_t wait = (next - esp_timer_get_time()) / 1000;
        uint8_t c;
        if (wait > 0 && uart_read_bytes(CONSOLE_UART, &c, 1, pdMS_TO_TICKS(wait)) == 1) {
            if (c == '\n' || c == '\r') {
                line[len] = '\0';
                len = 0;
                handle(line);
            } else if (len < CMD_LINE_MAX - 1) {
                line[len++] = c;
            }
            continue;
        }
        next = esp_timer_get_time() + (int64_t)period_ms * 1000;
        if (driver_running() && !driver_poll()) {
            printf("fault: driver trapped; stopped\n");
            driver_stop();
        }
    }
}

void app_main(void)
{
    uart_driver_install(CONSOLE_UART, 4096, 0, 0, NULL, 0);
    printf("\nbabel-host: ESP32-S3 + WAMR AOT, babel_v1\n");

    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, HOST_STACK);
    pthread_t t;
    if (pthread_create(&t, &attr, host_main, NULL) != 0) {
        printf("fault: could not start the host thread\n");
    }
}
