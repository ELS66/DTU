#include "supervision.h"
#include "event_log.h"
#include <stddef.h>
#include <string.h>
#include "module_blob.h"
#include "esp_attr.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static supervision_status_t status;
static esp_task_wdt_user_handle_t watchdog;
static const uint32_t budgets[MODULE_WATCH_COUNT] = {15000, 10000, 2000, 15000, 45000};
static const char *names[MODULE_WATCH_COUNT] = {"field_uart", "runtime_store", "indicators", "network", "modem_at"};
typedef struct { uint32_t magic, version, mask, reserved; uint64_t uptime_ms; uint32_t crc; } retained_t;
static RTC_NOINIT_ATTR retained_t retained;
static uint64_t now_ms(void) { return (uint64_t)(esp_timer_get_time() / 1000); }
const char *supervision_name(unsigned id) { return id < MODULE_WATCH_COUNT ? names[id] : "invalid"; }
void supervision_expect(module_watch_id_t id)
{
    ESP_ERROR_CHECK((unsigned)id < MODULE_WATCH_COUNT ? ESP_OK : ESP_ERR_INVALID_ARG);
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock);
    bool enabled = module_watch_enable(&status.watch, id, budgets[id], now);
    portEXIT_CRITICAL(&lock);
    ESP_ERROR_CHECK(enabled ? ESP_OK : ESP_ERR_INVALID_STATE);
}
void supervision_disable(module_watch_id_t id)
{
    portENTER_CRITICAL(&lock); module_watch_disable(&status.watch, id); portEXIT_CRITICAL(&lock);
    event_log_append(EVENT_TASK_DISABLED, (uint32_t)id, 0);
}
void supervision_progress(module_watch_id_t id)
{
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock); module_watch_progress(&status.watch, id, now); portEXIT_CRITICAL(&lock);
}
void supervision_get_status(supervision_status_t *out)
{
    portENTER_CRITICAL(&lock); *out = status; portEXIT_CRITICAL(&lock);
}
static void supervisor_task(void *unused)
{
    (void)unused;
    bool recorded = false;
    for (;;) {
        uint64_t now = now_ms();
        portENTER_CRITICAL(&lock);
        uint32_t mask = module_watch_evaluate(&status.watch, now);
        portEXIT_CRITICAL(&lock);
        if (!mask) ESP_ERROR_CHECK(esp_task_wdt_reset_user(watchdog));
        else if (!recorded) {
            retained_t failure = {.magic = UINT32_C(0x43355744), .version = 1, .mask = mask, .uptime_ms = now};
            failure.crc = module_blob_crc32((const uint8_t *)&failure, offsetof(retained_t, crc));
            retained = failure;
            recorded = true;
            event_log_append(EVENT_TASK_STALL, mask, 0);
            ESP_LOGE("supervision", "Task progress stalled mask=0x%02lx; watchdog feed stopped, RTC diagnosis retained", (unsigned long)mask);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
esp_err_t supervision_init(void)
{
    status.reset_reason = esp_reset_reason();
    status.previous_valid = retained.magic == UINT32_C(0x43355744) && retained.version == 1 &&
        retained.mask && !(retained.mask >> MODULE_WATCH_COUNT) &&
        retained.crc == module_blob_crc32((const uint8_t *)&retained, offsetof(retained_t, crc));
    if (status.previous_valid) {
        status.previous_mask = retained.mask; status.previous_ms = retained.uptime_ms;
        event_log_append(EVENT_PREVIOUS_STALL, retained.mask, 0);
    }
    memset(&retained, 0, sizeof(retained));
    const esp_task_wdt_config_t config = {.timeout_ms = 5000, .idle_core_mask = 1, .trigger_panic = true};
    esp_err_t error = esp_task_wdt_reconfigure(&config);
    if (error == ESP_ERR_INVALID_STATE) error = esp_task_wdt_init(&config);
    if (error != ESP_OK) return error;
    error = esp_task_wdt_add_user("module_progress", &watchdog);
    if (error != ESP_OK) return error;
    status.initialized = true;
    if (xTaskCreate(supervisor_task, "supervision", 4096, NULL, 5, NULL) != pdPASS) {
        status.initialized = false; esp_task_wdt_delete_user(watchdog); return ESP_ERR_NO_MEM;
    }
    ESP_LOGI("supervision", "Task budgets field/store/LED/net/modem=15/10/2/15/45s; TWDT panic=5s, previous_mask=0x%02lx",
             (unsigned long)status.previous_mask);
    return ESP_OK;
}
