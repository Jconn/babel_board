// Daughter NVM (24LC256) on the dedicated NVM bus, with write-protect control.
#pragma once

#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"

#define NVM_SIZE      32768
#define NVM_PAGE_SIZE 64

esp_err_t nvm_init(void);
esp_err_t nvm_read(uint16_t addr, void *out, size_t len);

// Programs an image from address 0 using the board-contract procedure:
// invalidate the header, write and verify the payload, write the header last.
// WP is released only inside this call. On failure *why names the step.
esp_err_t nvm_program(const uint8_t *image, size_t len, const char **why);

// Overwrites the header page with 0xff, leaving the board in provisioning mode.
esp_err_t nvm_invalidate(void);
