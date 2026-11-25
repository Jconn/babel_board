// Babel host API v1, as seen by a daughter-board driver compiled to wasm32.
// Draft: see board-contract-v0.md. Every import lives in the "babel_v1" module.
//
// A driver exports babel_driver_start/poll/stop (BABEL_EXPORT below):
//   start: 0 on success, negative on error.
//   poll:  0 with new measurements, 1 for no new sample, negative on error.
//   stop:  best effort; the board may already be gone.
// Measurements submitted during a poll are published only if it returns 0.

#ifndef BABEL_V1_H
#define BABEL_V1_H

#include <stdint.h>

#define BABEL_IMPORT(name) \
    __attribute__((import_module("babel_v1"), import_name(#name)))
#define BABEL_EXPORT(name) __attribute__((export_name(#name)))

// Error codes returned by the host.
#define BABEL_OK          0
#define BABEL_E_ARG      -1  // bad length, channel or argument
#define BABEL_E_DENIED   -2  // address not declared in the manifest
#define BABEL_E_BUS      -3  // NACK, timeout or bus fault
#define BABEL_E_FULL     -4  // too many measurements in one poll

// One I2C transaction to a 7-bit address declared in the manifest: write
// wr_len bytes, then (repeated start) read rd_len bytes. Either length may
// be 0. Each length is at most 64.
BABEL_IMPORT(i2c_transfer)
int32_t babel_i2c_transfer(int32_t addr7, const void *wr, uint32_t wr_len,
                           void *rd, uint32_t rd_len);

// Sleep; the host clamps the value to 0..1000 ms.
BABEL_IMPORT(delay_ms)
void babel_delay_ms(int32_t ms);

// Stage one measurement for a channel id declared in the manifest.
BABEL_IMPORT(submit)
int32_t babel_submit(int32_t channel, float value);

// Diagnostic text; the host prefixes and prints it.
BABEL_IMPORT(log)
void babel_log(const char *msg, uint32_t len);

#endif
