#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
#include "module_runtime_policy.h"
#include "module_supervision.h"
typedef struct {
    uint32_t rx_frames, bad_lengths, bad_checksums, partial_timeouts, partial_discards;
    uint32_t tx_frames, reply_timeouts, unsolicited, malformed, unsupported_events, uart_overflows;
    uint32_t aborted_requests, consecutive_timeouts, loss_events, recoveries;
    bool ever_valid;
    uint64_t last_valid_ms;
    module_contact_state_t contact_state;
    module_uart_health_t uart_health;
    uint32_t cache_failures, stale_param_replies, flush_failures;
} field_status_t;
esp_err_t field_bus_init(void);
esp_err_t field_bus_request(uint8_t command, const uint8_t *data, size_t size);
void field_bus_get_status(field_status_t *status);
uint64_t field_contact_timeout_ms(void);
