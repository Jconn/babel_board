// Daughter image: header, manifest and WAMR AOT module (board-contract-v0, format 3).
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define IMG_MAX_ADDRS    4
#define IMG_MAX_CHANNELS 8

typedef enum {
    IMG_OK,
    IMG_BLANK,    // header page erased: provisioning mode
    IMG_INVALID,  // present but failed a check: never executed
    IMG_IO,       // could not read the EEPROM
} img_status_t;

typedef struct {
    uint8_t id;
    char name[33];
    char unit[17];
} img_channel_t;

typedef struct {
    char board_type[48];
    char name[64];
    char driver_version[16];
    uint32_t i2c_hz;
    uint8_t addrs[IMG_MAX_ADDRS];
    int n_addrs;
    uint32_t startup_ms;
    uint32_t sample_period_ms;
    img_channel_t ch[IMG_MAX_CHANNELS];
    int n_ch;
    uint8_t *module;  // AOT bytes, heap-allocated; image_free releases it
    uint32_t module_len;
    uint32_t image_len;
} babel_image_t;

// Reads and fully validates the image in the daughter EEPROM.
img_status_t image_load(babel_image_t *img, char *why, size_t why_len);

// Same checks on an image held in RAM (before programming it).
img_status_t image_check(const uint8_t *buf, size_t len, babel_image_t *img, char *why, size_t why_len);

void image_free(babel_image_t *img);
