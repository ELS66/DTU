#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
#include "network_policy.h"
typedef struct {
    bool started, at_ready, power_pulsed;
    module_sim_t sim;
    int last_cme;
    uint32_t timeouts, uart_errors;
    int64_t observed_ms;
    char model[64], revision[64], pdp_ipv4[16];
    bool model_matches, attached, pdp_active, data_ready, socket_connected, apn_matches;
    unsigned registration, rssi;
    uint32_t socket_session, uncertain_sends;
    int64_t data_observed_ms;
} modem_status_t;
esp_err_t modem_init(void);
void modem_get_status(modem_status_t *out);
/* Bench TCP only. One socket, bounded 256-byte chunks, no automatic resend or TLS bypass. */
esp_err_t modem_tcp_open(const char *host, uint16_t port, uint32_t *session);
esp_err_t modem_tcp_write(uint32_t session, const uint8_t *bytes, size_t size);
esp_err_t modem_tcp_read(uint32_t session, uint8_t *bytes, size_t capacity, size_t *received);
esp_err_t modem_tcp_close(uint32_t session);
