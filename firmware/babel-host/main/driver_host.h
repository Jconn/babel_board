// Runs one daughter driver (WAMR AOT) against the babel_v1 host API.
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include "image.h"

bool driver_host_init(void);

// Loads, links and starts the image's module. On failure prints why and
// leaves nothing running.
bool driver_start(const babel_image_t *img);

// Calls babel_driver_poll and prints any published measurements.
// Returns false if the driver trapped or reported an error.
bool driver_poll(void);

// Best-effort babel_driver_stop, then frees the instance and module.
void driver_stop(void);

bool driver_running(void);
