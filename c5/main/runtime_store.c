#include "runtime_store.h"
#include "supervision.h"
#include "event_log.h"
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
static const char *TAG = "runtime";
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static runtime_status_t status;
static module_runtime_policy_t policy;
static nvs_handle_t store;
static uint32_t boot_tag;
static uint64_t now_ms(void) { return (uint64_t)(esp_timer_get_time() / 1000); }
uint64_t runtime_observation_timeout_ms(void)
{
    return module_state_timeout_ms(CONFIG_MODULE_BOARD_STALE_MS, CONFIG_MODULE_STATUS_POLL_MS, CONFIG_MODULE_REPLY_TIMEOUT_MS);
}
void runtime_get_status(runtime_status_t *out)
{
    portENTER_CRITICAL(&lock);
    *out = status;
    out->live = policy.live;
    out->saved_this_boot = policy.has_saved;
    out->last_success_ms = policy.last_success_ms;
    out->retry_after_ms = policy.retry_after_ms;
    out->duplicate_events = policy.duplicate_events;
    out->coalesced_changes = policy.coalesced_changes;
    out->pending = policy.live.known && policy.live.revision != policy.saved_revision;
    uint64_t anchor = policy.has_saved ? policy.last_success_ms : policy.first_observed_ms;
    portEXIT_CRITICAL(&lock);
    uint64_t now = now_ms();
    out->freshness = module_observation_freshness(&out->live, now, runtime_observation_timeout_ms());
    out->save_gap_ms = out->live.known && now >= anchor ? now - anchor : 0;
    out->blocked_stale = out->pending && out->freshness == MODULE_STATE_STALE;
    out->lagging = out->available && out->pending && out->freshness == MODULE_STATE_FRESH &&
                   out->save_gap_ms >= 15000;
    if (!out->init_attempted) out->storage_health = RUNTIME_STORAGE_STARTING;
    else if (!out->available) out->storage_health = RUNTIME_STORAGE_UNAVAILABLE;
    else if (out->sequence_exhausted) out->storage_health = RUNTIME_STORAGE_SEQUENCE_EXHAUSTED;
    else if (out->last_write_error != ESP_OK) out->storage_health = RUNTIME_STORAGE_WRITE_ERROR;
    else if (out->invalid_boot_slots && !out->saved_this_boot) out->storage_health = RUNTIME_STORAGE_READ_DEGRADED;
    else out->storage_health = RUNTIME_STORAGE_READY;
}
void runtime_observe(uint8_t command, uint8_t state, uint16_t remaining, bool urgent)
{
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock);
    bool changed = !policy.live.known || policy.live.state != state;
    bool accepted = module_runtime_observe(&policy, command, state, remaining, urgent, now);
    if (!accepted && status.rejected_observations != UINT32_MAX) ++status.rejected_observations;
    portEXIT_CRITICAL(&lock);
    if (accepted && changed) event_log_append(EVENT_BOARD_STATE, ((uint32_t)command << 8) | state, remaining);
}
static void store_task(void *argument)
{
    (void)argument;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(250));
        /* This point is reached again only after the previous NVS attempt returns. */
        supervision_progress(MODULE_WATCH_STORE);
        module_observation_t captured;
        module_save_reason_t reason;
        uint64_t now = now_ms(), sequence = 0;
        bool exhausted = false, captured_ok = false;
        portENTER_CRITICAL(&lock);
        if (!status.sequence_exhausted && module_runtime_save_due(&policy, now, runtime_observation_timeout_ms()) != MODULE_SAVE_NONE) {
            sequence = status.saved_valid ? status.saved.sequence + 1 : 1;
            if (!sequence) {
                status.sequence_exhausted = true;
                status.last_write_error = ESP_ERR_INVALID_STATE;
                exhausted = true;
            } else {
                captured_ok = module_runtime_capture(&policy, now, runtime_observation_timeout_ms(), &captured, &reason);
                if (captured_ok) status.last_attempt_ms = now;
            }
        }
        portEXIT_CRITICAL(&lock);
        if (exhausted) {
            event_log_append(EVENT_STORAGE_EXHAUSTED, 0, 0);
            ESP_LOGE(TAG, "Snapshot sequence exhausted; preserving history, recording disabled");
        }
        if (!captured_ok) continue;
        module_record_t record = {
            .sequence = sequence, .boot_tag = boot_tag, .state = captured.state,
            .source_command = captured.source_command, .remaining_seconds = captured.remaining_seconds,
            .observed_uptime_ms = captured.observed_uptime_ms,
        };
        uint8_t bytes[MODULE_RECORD_SIZE];
        module_record_encode(&record, bytes);
        esp_err_t error = nvs_set_blob(store, (record.sequence & 1) ? "record1" : "record0", bytes, sizeof(bytes));
        if (error == ESP_OK) error = nvs_commit(store);
        uint64_t completed = now_ms();
        portENTER_CRITICAL(&lock);
        module_runtime_save_finished(&policy, captured.revision, error == ESP_OK, completed);
        esp_err_t previous_error = status.last_write_error;
        status.last_write_error = error;
        if (error == ESP_OK) {
            status.saved_valid = true; status.saved = record; status.last_save_reason = reason;
            if (status.writes_ok != UINT32_MAX) ++status.writes_ok;
        } else if (status.write_failures != UINT32_MAX) ++status.write_failures;
        portEXIT_CRITICAL(&lock);
        if (error != ESP_OK && previous_error != error)
            event_log_append(EVENT_STORAGE_WRITE_FAILURE, (uint32_t)error, 0);
        else if (error == ESP_OK && previous_error != ESP_OK)
            event_log_append(EVENT_STORAGE_RECOVERED, (uint32_t)previous_error, 0);
        if (error != ESP_OK)
            ESP_LOGE(TAG, "Snapshot failed: %s; retry in 5s, RAM history retained, no erase", esp_err_to_name(error));
        else
            ESP_LOGI(TAG, "Saved #%" PRIu64 " state=%u remaining=%us reason=%d",
                     record.sequence, record.state, record.remaining_seconds, reason);
    }
}
static esp_err_t initialization_failed(esp_err_t error)
{
    portENTER_CRITICAL(&lock);
    status.init_error = error; status.available = false;
    portEXIT_CRITICAL(&lock);
    event_log_append(EVENT_STORAGE_INIT_FAILURE, (uint32_t)error, 0);
    return error;
}
esp_err_t runtime_store_init(void)
{
    portENTER_CRITICAL(&lock); status.init_attempted = true; portEXIT_CRITICAL(&lock);
    boot_tag = esp_random();
    esp_err_t error = nvs_flash_init_partition("runtime");
    if (error != ESP_OK) return initialization_failed(error);
    error = nvs_open_from_partition("runtime", "observations", NVS_READWRITE, &store);
    if (error != ESP_OK) return initialization_failed(error);
    for (unsigned slot = 0; slot < 2; ++slot) {
        uint8_t bytes[MODULE_RECORD_SIZE];
        size_t size = sizeof(bytes);
        error = nvs_get_blob(store, slot ? "record1" : "record0", bytes, &size);
        if (error == ESP_ERR_NVS_NOT_FOUND) continue;
        module_record_t record;
        if (error != ESP_OK || !module_record_decode(bytes, size, &record)) {
            ++status.invalid_boot_slots;
            event_log_append(EVENT_STORAGE_INVALID_SLOT, slot, (uint32_t)error);
            ESP_LOGW(TAG, "Invalid snapshot slot %u (%s); retained without erase", slot, esp_err_to_name(error));
            continue;
        }
        if (!status.saved_valid || record.sequence > status.saved.sequence) {
            status.saved_valid = true; status.saved = record;
        }
    }
    if (status.saved_valid)
        ESP_LOGI(TAG, "Historical #%" PRIu64 " remaining=%us; waiting for board query",
                 status.saved.sequence, status.saved.remaining_seconds);
    supervision_expect(MODULE_WATCH_STORE);
    if (xTaskCreate(store_task, "runtime_store", 4096, NULL, 3, NULL) != pdPASS) {
        supervision_disable(MODULE_WATCH_STORE);
        nvs_close(store); return initialization_failed(ESP_ERR_NO_MEM);
    }
    portENTER_CRITICAL(&lock); status.available = true; status.init_error = ESP_OK; portEXIT_CRITICAL(&lock);
    return ESP_OK;
}
