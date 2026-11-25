// Step-by-step narration for the TRACE command (firmware/tools/babel_trace.py).
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

extern bool g_trace;       // narrate discovery, loading and linking
extern int g_trace_polls;  // also show I2C traffic for this many more polls

#define TRACE(...) do { if (g_trace) printf("    " __VA_ARGS__); } while (0)
#define SECTION(title) do { if (g_trace) printf("\n== %s ==\n", title); } while (0)

static inline void trace_hex(const char *label, const uint8_t *d, int n)
{
    if (!g_trace) {
        return;
    }
    printf("    %s", label);
    for (int i = 0; i < n; i++) {
        printf("%s%02x", i % 16 ? " " : "\n      ", d[i]);
    }
    printf("\n");
}
