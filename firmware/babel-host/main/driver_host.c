#include "driver_host.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/i2c_master.h"
#include "esp_rom_sys.h"
#include "wasm_export.h"
#include "esp_timer.h"
#include "pins.h"
#include "trace.h"

// babel_v1 error codes (see firmware/drivers/include/babel_v1.h).
#define BABEL_OK        0
#define BABEL_E_ARG    -1
#define BABEL_E_DENIED -2
#define BABEL_E_BUS    -3
#define BABEL_E_FULL   -4

#define XFER_MAX       64
#define XFER_TIMEOUT   50    // ms per bus transaction
#define WASM_STACK     8192  // bytes, guest operand/call stack
#define DELAY_MAX_MS   1000

static wasm_module_t module;
static wasm_module_inst_t inst;
static wasm_exec_env_t env;
static wasm_function_inst_t f_start, f_poll, f_stop;

static babel_image_t img;  // manifest limits; module bytes stay owned by the caller
static i2c_master_bus_handle_t sensor_bus;
static i2c_master_dev_handle_t devs[IMG_MAX_ADDRS];

static struct {
    uint8_t ch;
    float value;
} staged[IMG_MAX_CHANNELS];
static int n_staged;

// ---- babel_v1 natives. WAMR has already bounds-checked every *~ buffer. ----

static int32_t n_i2c_transfer(wasm_exec_env_t e, int32_t addr, const uint8_t *wr, uint32_t wr_len,
                              uint8_t *rd, uint32_t rd_len)
{
    if (wr_len > XFER_MAX || rd_len > XFER_MAX || (wr_len == 0 && rd_len == 0)) {
        return BABEL_E_ARG;
    }
    i2c_master_dev_handle_t dev = NULL;
    for (int i = 0; i < img.n_addrs; i++) {
        if (img.addrs[i] == addr) {
            dev = devs[i];
        }
    }
    if (!dev) {
        return BABEL_E_DENIED;
    }
    esp_err_t err;
    if (wr_len && rd_len) {
        err = i2c_master_transmit_receive(dev, wr, wr_len, rd, rd_len, XFER_TIMEOUT);
    } else if (wr_len) {
        err = i2c_master_transmit(dev, wr, wr_len, XFER_TIMEOUT);
    } else {
        err = i2c_master_receive(dev, rd, rd_len, XFER_TIMEOUT);
    }
    if (g_trace_polls > 0) {
        printf("    i2c 0x%02lx  write", (long)addr);
        for (uint32_t i = 0; i < wr_len; i++) {
            printf(" %02x", wr[i]);
        }
        printf("  read");
        for (uint32_t i = 0; i < rd_len; i++) {
            printf(" %02x", rd[i]);
        }
        printf("  %s\n", err == ESP_OK ? "ok" : esp_err_to_name(err));
    }
    return err == ESP_OK ? BABEL_OK : BABEL_E_BUS;
}

static void n_delay_ms(wasm_exec_env_t e, int32_t ms)
{
    if (ms <= 0) {
        return;
    }
    if (ms > DELAY_MAX_MS) {
        ms = DELAY_MAX_MS;
    }
    if (ms < portTICK_PERIOD_MS) {
        esp_rom_delay_us(ms * 1000);
    } else {
        vTaskDelay(pdMS_TO_TICKS(ms));
    }
}

static int32_t n_submit(wasm_exec_env_t e, int32_t channel, float value)
{
    bool declared = false;
    for (int i = 0; i < img.n_ch; i++) {
        declared |= img.ch[i].id == channel;
    }
    if (!declared) {
        return BABEL_E_ARG;
    }
    if (n_staged >= img.n_ch) {
        return BABEL_E_FULL;
    }
    if (g_trace_polls > 0) {
        printf("    submit channel %ld = %.2f\n", (long)channel, value);
    }
    staged[n_staged].ch = channel;
    staged[n_staged].value = value;
    n_staged++;
    return BABEL_OK;
}

static void n_log(wasm_exec_env_t e, const char *msg, uint32_t len)
{
    printf("[driver] %.*s\n", (int)(len > 120 ? 120 : len), msg);
}

static NativeSymbol natives[] = {
    { "i2c_transfer", n_i2c_transfer, "(i*~*~)i", NULL },
    { "delay_ms", n_delay_ms, "(i)", NULL },
    { "submit", n_submit, "(if)i", NULL },
    { "log", n_log, "(*~)", NULL },
};

// ---- runtime ----

bool driver_host_init(void)
{
    RuntimeInitArgs args;
    memset(&args, 0, sizeof args);
    args.mem_alloc_type = Alloc_With_Allocator;
    args.mem_alloc_option.allocator.malloc_func = (void *)malloc;
    args.mem_alloc_option.allocator.realloc_func = (void *)realloc;
    args.mem_alloc_option.allocator.free_func = (void *)free;
    if (!wasm_runtime_full_init(&args)) {
        printf("WAMR init failed\n");
        return false;
    }
    if (!wasm_runtime_register_natives("babel_v1", natives, sizeof natives / sizeof natives[0])) {
        printf("WAMR native registration failed\n");
        return false;
    }
    return true;
}

static bool bus_open(void)
{
    i2c_master_bus_config_t cfg = {
        .i2c_port = -1,
        .sda_io_num = PIN_SENSOR_SDA,
        .scl_io_num = PIN_SENSOR_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,
    };
    if (i2c_new_master_bus(&cfg, &sensor_bus) != ESP_OK) {
        return false;
    }
    for (int i = 0; i < img.n_addrs; i++) {
        i2c_device_config_t dev = {
            .dev_addr_length = I2C_ADDR_BIT_LEN_7,
            .device_address = img.addrs[i],
            .scl_speed_hz = img.i2c_hz,
        };
        if (i2c_master_bus_add_device(sensor_bus, &dev, &devs[i]) != ESP_OK) {
            return false;
        }
    }
    return true;
}

static void bus_close(void)
{
    for (int i = 0; i < IMG_MAX_ADDRS; i++) {
        if (devs[i]) {
            i2c_master_bus_rm_device(devs[i]);
            devs[i] = NULL;
        }
    }
    if (sensor_bus) {
        i2c_del_master_bus(sensor_bus);
        sensor_bus = NULL;
    }
}

static void teardown(void)
{
    if (env) {
        wasm_runtime_destroy_exec_env(env);
    }
    if (inst) {
        wasm_runtime_deinstantiate(inst);
    }
    if (module) {
        wasm_runtime_unload(module);
    }
    env = NULL;
    inst = NULL;
    module = NULL;
    f_start = f_poll = f_stop = NULL;
    bus_close();
}

// Imports must all be babel_v1 functions this host provides, with matching signatures.
static bool check_imports(void)
{
    int32_t n = wasm_runtime_get_import_count(module);
    for (int32_t i = 0; i < n; i++) {
        wasm_import_t im;
        wasm_runtime_get_import_type(module, i, &im);
        bool known = false;
        for (size_t k = 0; k < sizeof natives / sizeof natives[0]; k++) {
            known |= strcmp(im.name, natives[k].symbol) == 0;
        }
        if (im.kind != WASM_IMPORT_EXPORT_KIND_FUNC || strcmp(im.module_name, "babel_v1") != 0 || !known) {
            printf("driver rejected: import %s.%s is not part of babel_v1\n", im.module_name, im.name);
            return false;
        }
        if (!im.linked) {
            printf("driver rejected: import babel_v1.%s has the wrong signature\n", im.name);
            return false;
        }
        for (size_t k = 0; k < sizeof natives / sizeof natives[0]; k++) {
            if (strcmp(im.name, natives[k].symbol) == 0) {
                TRACE("import babel_v1.%-13s %-10s -> host native, linked\n", im.name, natives[k].signature);
            }
        }
    }
    return true;
}

// Exports must be () -> i32.
static wasm_function_inst_t entry(const char *name)
{
    wasm_function_inst_t f = wasm_runtime_lookup_function(inst, name);
    wasm_valkind_t result;
    if (!f || wasm_func_get_param_count(f, inst) != 0 || wasm_func_get_result_count(f, inst) != 1) {
        printf("driver rejected: export %s missing or not () -> i32\n", name);
        return NULL;
    }
    wasm_func_get_result_types(f, inst, &result);
    if (result != WASM_I32) {
        printf("driver rejected: export %s does not return i32\n", name);
        return NULL;
    }
    TRACE("export %-20s () -> i32  found\n", name);
    return f;
}

static bool call(wasm_function_inst_t f, const char *name, int32_t *ret)
{
    uint32_t argv[1] = { 0 };
    if (!wasm_runtime_call_wasm(env, f, 0, argv)) {
        printf("driver trapped in %s: %s\n", name, wasm_runtime_get_exception(inst));
        wasm_runtime_clear_exception(inst);
        return false;
    }
    *ret = (int32_t)argv[0];
    return true;
}

bool driver_start(const babel_image_t *image)
{
    char err[128];
    img = *image;
    uint32_t maj, min, pat;
    wasm_runtime_get_version(&maj, &min, &pat);

    SECTION("4. Load the AOT module into WAMR");
    TRACE("WAMR %lu.%lu.%lu, AOT only, target xtensa-esp32s3\n", (unsigned long)maj,
          (unsigned long)min, (unsigned long)pat);
    TRACE("wasm_runtime_load(%lu bytes): relocates the Xtensa code into executable RAM\n",
          (unsigned long)image->module_len);
    int64_t t0 = esp_timer_get_time();
    module = wasm_runtime_load(image->module, image->module_len, err, sizeof err);
    if (!module) {
        printf("driver rejected: AOT load failed: %s\n", err);
        goto fail;
    }
    TRACE("loaded in %lld us\n", esp_timer_get_time() - t0);

    SECTION("5. Link imports to the babel_v1 host API");
    if (!check_imports()) {
        goto fail;
    }

    SECTION("6. Instantiate and find the driver entry points");
    t0 = esp_timer_get_time();
    inst = wasm_runtime_instantiate(module, WASM_STACK, 0, err, sizeof err);
    if (!inst) {
        printf("driver rejected: instantiate failed: %s\n", err);
        goto fail;
    }
    TRACE("instantiated in %lld us: 64 KiB linear memory, %d-byte stack\n",
          esp_timer_get_time() - t0, WASM_STACK);
    if (!(f_start = entry("babel_driver_start")) || !(f_poll = entry("babel_driver_poll"))
        || !(f_stop = entry("babel_driver_stop"))) {
        goto fail;
    }
    env = wasm_runtime_create_exec_env(inst, WASM_STACK);
    if (!env) {
        printf("driver rejected: no exec env\n");
        goto fail;
    }
    if (!bus_open()) {
        printf("sensor bus setup failed\n");
        goto fail;
    }

    SECTION("7. Start the driver");
    TRACE("sensor bus up: GPIO%d SCL, GPIO%d SDA, %lu Hz; driver may reach 0x%02x only\n",
          PIN_SENSOR_SCL, PIN_SENSOR_SDA, (unsigned long)img.i2c_hz, img.addrs[0]);
    TRACE("waiting startup_ms = %lu, then calling babel_driver_start()\n", (unsigned long)img.startup_ms);
    vTaskDelay(pdMS_TO_TICKS(img.startup_ms));
    if (g_trace) {
        g_trace_polls++;  // show the start call's I2C traffic too
    }
    int32_t ret;
    if (!call(f_start, "babel_driver_start", &ret)) {
        goto fail;
    }
    if (g_trace) {
        g_trace_polls--;
    }
    if (ret != 0) {
        printf("babel_driver_start returned %ld\n", (long)ret);
        goto fail;
    }
    TRACE("babel_driver_start() returned 0\n");
    return true;

fail:
    teardown();
    return false;
}

bool driver_poll(void)
{
    int32_t ret;
    n_staged = 0;
    if (g_trace_polls > 0) {
        printf("  babel_driver_poll():\n");
    }
    bool ok = call(f_poll, "babel_driver_poll", &ret);
    if (g_trace_polls > 0) {
        g_trace_polls--;
        if (ok) {
            printf("    returned %ld -> publish:\n  ", (long)ret);
        }
    }
    if (!ok) {
        return false;
    }
    if (ret < 0) {
        printf("poll error %ld\n", (long)ret);
        return true;
    }
    if (ret == 0) {  // publish what was staged; discard on error or no-sample
        for (int i = 0; i < n_staged; i++) {
            for (int c = 0; c < img.n_ch; c++) {
                if (img.ch[c].id == staged[i].ch) {
                    printf("%s %7.2f %s   ", img.ch[c].name, staged[i].value, img.ch[c].unit);
                }
            }
        }
        printf("\n");
    }
    return true;
}

void driver_stop(void)
{
    if (f_stop) {
        int32_t ret;
        call(f_stop, "babel_driver_stop", &ret);  // best effort
    }
    teardown();
}

bool driver_running(void)
{
    return f_poll != NULL;
}
