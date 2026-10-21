#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "network_policy.h"
typedef struct {
    bool initialized, wifi_ip, provisioning, candidate, saved_credentials, boot_decided;
    module_net_action_t boot_action;
    uint8_t channel;
    int8_t rssi;
    uint16_t disconnect_reason;
    uint32_t ipv4, dropped_events;
    esp_err_t save_error, last_error;
} network_status_t;
esp_err_t network_init(void);
esp_err_t network_request_provision(void);
void network_get_status(network_status_t *out);
