#include "image.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"
#include "mbedtls/sha256.h"
#include "wasm_export.h"
#include "nvm.h"

#define MAGIC          "BABELW01"
#define FORMAT_VERSION 3
#define API_VERSION    1
#define HEADER_SIZE    64
#define MANIFEST_ADDR  0x0040
#define MANIFEST_MAX   960
#define MODULE_ADDR    0x0400
#define MODULE_MAX     28672
#define AOT_TARGET     "xtensa-esp32s3"
#define I2C_HZ_MAX     100000

// Where image bytes come from: the EEPROM or a RAM buffer.
typedef struct {
    const uint8_t *buf;  // NULL: read the EEPROM
    size_t len;
} source_t;

static bool src_read(const source_t *s, uint32_t addr, void *out, size_t n)
{
    if (!s->buf) {
        return nvm_read(addr, out, n) == ESP_OK;
    }
    if (addr + n > s->len) {
        return false;
    }
    memcpy(out, s->buf + addr, n);
    return true;
}

static uint16_t le16(const uint8_t *p) { return p[0] | p[1] << 8; }
static uint32_t le32(const uint8_t *p) { return le16(p) | (uint32_t)le16(p + 2) << 16; }

#define FAIL(...) do { snprintf(why, why_len, __VA_ARGS__); goto invalid; } while (0)

static bool copy_str(char *dst, size_t cap, const cJSON *item)
{
    if (!cJSON_IsString(item) || strlen(item->valuestring) >= cap) {
        return false;
    }
    strcpy(dst, item->valuestring);
    return true;
}

static img_status_t parse_manifest(const char *json, babel_image_t *img, char *why, size_t why_len)
{
    cJSON *m = cJSON_Parse(json);
    if (!m) {
        snprintf(why, why_len, "manifest is not valid JSON");
        return IMG_INVALID;
    }
    const cJSON *it;
    char ver[16] = "?", want_ver[16];
    uint32_t maj, min, pat;
    wasm_runtime_get_version(&maj, &min, &pat);
    snprintf(want_ver, sizeof want_ver, "%lu.%lu.%lu", (unsigned long)maj, (unsigned long)min, (unsigned long)pat);

    if (!copy_str(img->board_type, sizeof img->board_type, cJSON_GetObjectItem(m, "board_type"))
        || !copy_str(img->name, sizeof img->name, cJSON_GetObjectItem(m, "name"))
        || !copy_str(img->driver_version, sizeof img->driver_version, cJSON_GetObjectItem(m, "driver_version"))) {
        FAIL("manifest board_type/name/driver_version missing or too long");
    }
    it = cJSON_GetObjectItem(m, "runtime");
    if (!cJSON_IsString(it) || strcmp(it->valuestring, "wamr-aot") != 0) {
        FAIL("runtime is not wamr-aot");
    }
    it = cJSON_GetObjectItem(m, "aot_target");
    if (!cJSON_IsString(it) || strcmp(it->valuestring, AOT_TARGET) != 0) {
        FAIL("aot_target is not %s", AOT_TARGET);
    }
    if (!copy_str(ver, sizeof ver, cJSON_GetObjectItem(m, "wamr_version")) || strcmp(ver, want_ver) != 0) {
        FAIL("AOT built for WAMR %s; host runs %s", ver, want_ver);
    }
    it = cJSON_GetObjectItem(m, "babel_api_major");
    if (!cJSON_IsNumber(it) || it->valueint != API_VERSION) {
        FAIL("babel_api_major is not %d", API_VERSION);
    }
    it = cJSON_GetObjectItem(m, "required_capabilities");
    if (!cJSON_IsArray(it)) {
        FAIL("required_capabilities missing");
    }
    const cJSON *e;
    cJSON_ArrayForEach(e, it) {
        if (!cJSON_IsString(e) || strcmp(e->valuestring, "i2c.transfer.v1") != 0) {
            FAIL("unsupported capability %s", cJSON_IsString(e) ? e->valuestring : "?");
        }
    }

    const cJSON *intf = cJSON_GetObjectItem(m, "interface");
    it = cJSON_GetObjectItem(intf, "kind");
    if (!cJSON_IsString(it) || strcmp(it->valuestring, "i2c") != 0) {
        FAIL("interface kind is not i2c (only i2c is supported so far)");
    }
    it = cJSON_GetObjectItem(intf, "frequency_hz");
    if (!cJSON_IsNumber(it) || it->valuedouble < 10000) {
        FAIL("interface frequency_hz missing or below 10 kHz");
    }
    img->i2c_hz = it->valuedouble > I2C_HZ_MAX ? I2C_HZ_MAX : (uint32_t)it->valuedouble;
    it = cJSON_GetObjectItem(intf, "addresses");
    img->n_addrs = cJSON_GetArraySize(it);
    if (!cJSON_IsArray(it) || img->n_addrs < 1 || img->n_addrs > IMG_MAX_ADDRS) {
        FAIL("interface addresses: need 1..%d", IMG_MAX_ADDRS);
    }
    for (int i = 0; i < img->n_addrs; i++) {
        int a = cJSON_GetArrayItem(it, i)->valueint;
        if (a < 0x08 || a > 0x77) {
            FAIL("address 0x%02x is not a 7-bit unicast address", a);
        }
        img->addrs[i] = a;
    }

    it = cJSON_GetObjectItem(m, "startup_ms");
    img->startup_ms = cJSON_IsNumber(it) && it->valueint >= 0 ? it->valueint : 0;
    if (img->startup_ms > 2000) {
        FAIL("startup_ms over the 2000 ms host limit");
    }
    it = cJSON_GetObjectItem(m, "sample_period_ms");
    img->sample_period_ms = cJSON_IsNumber(it) && it->valueint >= 100 ? it->valueint : 100;

    it = cJSON_GetObjectItem(m, "channels");
    img->n_ch = cJSON_GetArraySize(it);
    if (!cJSON_IsArray(it) || img->n_ch < 1 || img->n_ch > IMG_MAX_CHANNELS) {
        FAIL("channels: need 1..%d", IMG_MAX_CHANNELS);
    }
    for (int i = 0; i < img->n_ch; i++) {
        const cJSON *c = cJSON_GetArrayItem(it, i);
        const cJSON *id = cJSON_GetObjectItem(c, "id");
        if (!cJSON_IsNumber(id) || id->valueint < 0 || id->valueint > 255
            || !copy_str(img->ch[i].name, sizeof img->ch[i].name, cJSON_GetObjectItem(c, "name"))
            || !copy_str(img->ch[i].unit, sizeof img->ch[i].unit, cJSON_GetObjectItem(c, "unit"))) {
            FAIL("channel %d malformed", i);
        }
        img->ch[i].id = id->valueint;
        for (int j = 0; j < i; j++) {
            if (img->ch[j].id == img->ch[i].id) {
                FAIL("duplicate channel id %d", id->valueint);
            }
        }
    }
    cJSON_Delete(m);
    return IMG_OK;

invalid:
    cJSON_Delete(m);
    return IMG_INVALID;
}

static img_status_t load(const source_t *src, babel_image_t *img, char *why, size_t why_len)
{
    memset(img, 0, sizeof *img);
    uint8_t h[HEADER_SIZE];
    char *manifest = NULL;
    uint8_t *module = NULL;

    if (!src_read(src, 0, h, sizeof h)) {
        snprintf(why, why_len, "could not read the header");
        return src->buf ? IMG_INVALID : IMG_IO;
    }
    bool blank = true;
    for (int i = 0; i < 8; i++) {
        blank &= h[i] == 0xff;
    }
    if (blank) {
        snprintf(why, why_len, "header is blank");
        return IMG_BLANK;
    }

    // Fixed fields and lengths before allocating or reading payloads.
    if (memcmp(h, MAGIC, 8) != 0) {
        FAIL("bad magic");
    }
    uint16_t fmt = le16(h + 8), api = le16(h + 10), mlen = le16(h + 12);
    uint32_t modlen = le32(h + 16);
    if (fmt != FORMAT_VERSION) {
        FAIL("format %u, host supports %d (WAMR AOT)", fmt, FORMAT_VERSION);
    }
    if (api != API_VERSION) {
        FAIL("driver API %u, host supports %d", api, API_VERSION);
    }
    if (mlen < 1 || mlen > MANIFEST_MAX || modlen < 8 || modlen > MODULE_MAX) {
        FAIL("manifest length %u or module length %lu out of range", mlen, (unsigned long)modlen);
    }
    if (le16(h + 14) != 0) {
        FAIL("reserved header bytes are not zero");
    }
    for (int i = 52; i < 64; i++) {
        if (h[i] != 0) {
            FAIL("reserved header bytes are not zero");
        }
    }

    manifest = malloc(mlen + 1);
    module = malloc(modlen);
    if (!manifest || !module) {
        FAIL("out of memory");
    }
    if (!src_read(src, MANIFEST_ADDR, manifest, mlen) || !src_read(src, MODULE_ADDR, module, modlen)) {
        free(manifest);
        free(module);
        snprintf(why, why_len, "could not read the payload");
        return src->buf ? IMG_INVALID : IMG_IO;
    }
    manifest[mlen] = '\0';

    uint8_t digest[32];
    mbedtls_sha256_context sha;
    mbedtls_sha256_init(&sha);
    mbedtls_sha256_starts(&sha, 0);
    mbedtls_sha256_update(&sha, h, 20);
    mbedtls_sha256_update(&sha, (const uint8_t *)manifest, mlen);
    mbedtls_sha256_update(&sha, module, modlen);
    mbedtls_sha256_finish(&sha, digest);
    mbedtls_sha256_free(&sha);
    if (memcmp(digest, h + 20, 32) != 0) {
        FAIL("SHA-256 mismatch: image is corrupt or partly written");
    }
    if (strlen(manifest) != mlen) {
        FAIL("manifest contains a NUL byte");
    }
    if (memcmp(module, "\0aot", 4) != 0) {
        FAIL("module is not a WAMR AOT file");
    }

    img_status_t st = parse_manifest(manifest, img, why, why_len);
    free(manifest);
    manifest = NULL;
    if (st != IMG_OK) {
        free(module);
        return st;
    }
    img->module = module;
    img->module_len = modlen;
    img->image_len = MODULE_ADDR + modlen;
    return IMG_OK;

invalid:
    free(manifest);
    free(module);
    return IMG_INVALID;
}

img_status_t image_load(babel_image_t *img, char *why, size_t why_len)
{
    source_t src = { 0 };
    return load(&src, img, why, why_len);
}

img_status_t image_check(const uint8_t *buf, size_t len, babel_image_t *img, char *why, size_t why_len)
{
    source_t src = { buf, len };
    return load(&src, img, why, why_len);
}

void image_free(babel_image_t *img)
{
    free(img->module);
    img->module = NULL;
}
