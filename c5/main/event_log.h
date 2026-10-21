#pragma once
#include "module_events.h"
/* Numeric fields only: no SSID, credentials, hostnames or arbitrary UART payload. */
typedef enum {
    EVENT_BOOT = 1, EVENT_PREVIOUS_STALL = 2,
    EVENT_BOARD_OFFLINE = 10, EVENT_BOARD_RECOVERED = 11, EVENT_BOARD_STATE = 12,
    EVENT_UART_FAULT = 20, EVENT_UART_RECOVERED = 21, EVENT_CACHE_FAILURE = 22,
    EVENT_STALE_PARAM_REPLY = 23, EVENT_UART_TX_FAILURE = 24,
    EVENT_STORAGE_INIT_FAILURE = 30, EVENT_STORAGE_INVALID_SLOT = 31,
    EVENT_STORAGE_WRITE_FAILURE = 32, EVENT_STORAGE_RECOVERED = 33, EVENT_STORAGE_EXHAUSTED = 34,
    EVENT_WIFI_READY = 40, EVENT_WIFI_DOWN = 41, EVENT_PROVISION_START = 42, EVENT_PROVISION_END = 43,
    EVENT_NETWORK_DROPS = 44, EVENT_NETWORK_ERROR = 45, EVENT_WIFI_SAVE_ERROR = 46,
    EVENT_MODEM_SIM = 50, EVENT_MODEM_REGISTRATION = 51, EVENT_MODEM_DATA = 52, EVENT_MODEM_AT = 53,
    EVENT_TASK_STALL = 60, EVENT_TASK_DISABLED = 61, EVENT_COMPONENT_FAILURE = 70
} event_code_t;
void event_log_init(void);
void event_log_append(event_code_t code, uint32_t detail, uint32_t value);
bool event_log_page(uint64_t after, size_t limit, module_events_page_t *page, uint32_t *boot_tag);
const char *event_log_name(uint32_t code);
