#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
#include "network_policy.h"
typedef enum { UPLINK_AUTO, UPLINK_WIFI, UPLINK_LTE } uplink_mode_t;
typedef struct {
    bool initialized, active;
    module_link_t route, last_success;
    uint32_t token, wifi_failures, lte_failures, uncertain_writes;
    uint64_t wifi_retry_after_ms;
    esp_err_t last_error;
} uplink_status_t;
/* Plain TCP bench adapter, one fenced connection. TLS/authentication belongs above this layer. */
esp_err_t uplink_init(void);
void uplink_get_status(uplink_status_t *out);
esp_err_t uplink_open(uplink_mode_t mode, const char *host, uint16_t port, uint32_t *token);
esp_err_t uplink_write(uint32_t token, const uint8_t *bytes, size_t size);
esp_err_t uplink_read(uint32_t token, uint8_t *bytes, size_t capacity, size_t *received, unsigned timeout_ms);
esp_err_t uplink_close(uint32_t token);
