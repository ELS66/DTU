#include "event_log.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static module_events_t events;
static uint32_t boot_tag;
void event_log_init(void)
{
    module_events_init(&events); boot_tag = esp_random();
    event_log_append(EVENT_BOOT, (uint32_t)esp_reset_reason(), 0);
}
void event_log_append(event_code_t code, uint32_t detail, uint32_t value)
{
    uint64_t now = (uint64_t)(esp_timer_get_time() / 1000);
    portENTER_CRITICAL(&lock);
    module_events_append(&events, code, detail, value, now);
    portEXIT_CRITICAL(&lock);
}
bool event_log_page(uint64_t after, size_t limit, module_events_page_t *page, uint32_t *tag)
{
    portENTER_CRITICAL(&lock);
    bool ok = module_events_page(&events, after, limit, page);
    if (tag) *tag = boot_tag;
    portEXIT_CRITICAL(&lock);
    return ok;
}
const char *event_log_name(uint32_t code)
{
    switch (code) {
#define NAME(code) case EVENT_##code: return #code
        NAME(BOOT); NAME(PREVIOUS_STALL); NAME(BOARD_OFFLINE); NAME(BOARD_RECOVERED); NAME(BOARD_STATE);
        NAME(UART_FAULT); NAME(UART_RECOVERED); NAME(CACHE_FAILURE); NAME(STALE_PARAM_REPLY); NAME(UART_TX_FAILURE);
        NAME(STORAGE_INIT_FAILURE); NAME(STORAGE_INVALID_SLOT); NAME(STORAGE_WRITE_FAILURE); NAME(STORAGE_RECOVERED);
        NAME(STORAGE_EXHAUSTED); NAME(WIFI_READY); NAME(WIFI_DOWN); NAME(PROVISION_START); NAME(PROVISION_END);
        NAME(NETWORK_DROPS); NAME(NETWORK_ERROR); NAME(WIFI_SAVE_ERROR);
        NAME(MODEM_SIM); NAME(MODEM_REGISTRATION); NAME(MODEM_DATA); NAME(MODEM_AT);
        NAME(TASK_STALL); NAME(TASK_DISABLED); NAME(COMPONENT_FAILURE);
#undef NAME
    default: return "UNKNOWN";
    }
}
