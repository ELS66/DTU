#include <inttypes.h>
#include "board.h"
#include "diagnostics.h"
#include "field_bus.h"
#include "runtime_store.h"
#include "modem.h"
#include "network.h"
#include "uplink.h"
#include "indicators.h"
#include "supervision.h"
#include "board_cache.h"
#include "event_log.h"
#include "esp_app_desc.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_system.h"
#include "nvs_flash.h"

void app_main(void)
{
    event_log_init();
    ESP_ERROR_CHECK(board_init());
    ESP_ERROR_CHECK(supervision_init());
    ESP_ERROR_CHECK(indicators_init());
    esp_chip_info_t chip;
    esp_chip_info(&chip);
    uint32_t flash_size = 0;
    ESP_ERROR_CHECK(esp_flash_get_size(NULL, &flash_size));
    ESP_LOGI("boot", "V0.14.4 / %s / IDF %s / chip revision=%u / reset=%d",
             esp_app_get_description()->version, esp_get_idf_version(), chip.revision, esp_reset_reason());
    ESP_LOGI("boot", "Flash=%" PRIu32 " bytes PSRAM=%u bytes internal_heap=%u",
             flash_size, (unsigned)esp_psram_get_size(),
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
    if (flash_size != 8 * 1024 * 1024 || esp_psram_get_size() != 8 * 1024 * 1024)
        ESP_LOGW("boot", "Expected N8R8 8MB Flash + 8MB PSRAM; verify actual module");
    /* Do not auto-erase credentials or historical runtime data on initialization errors. */
    esp_err_t storage_error = nvs_flash_init();
    if (storage_error != ESP_OK) event_log_append(EVENT_COMPONENT_FAILURE, 0, (uint32_t)storage_error);
    if (storage_error != ESP_OK)
        ESP_LOGE("boot", "System NVS unavailable (%s); no automatic erase", esp_err_to_name(storage_error));
    storage_error = runtime_store_init();
    if (storage_error != ESP_OK)
        ESP_LOGE("boot", "Runtime persistence unavailable (%s); TTL/USB diagnostic mode",
                 esp_err_to_name(storage_error));
    ESP_ERROR_CHECK(board_cache_init());
    ESP_ERROR_CHECK(field_bus_init());
    esp_err_t error = modem_init();
    if (error != ESP_OK) event_log_append(EVENT_COMPONENT_FAILURE, 1, (uint32_t)error);
    esp_err_t modem_error = error;
    if (error != ESP_OK) ESP_LOGE("boot", "Modem initialization failed: %s", esp_err_to_name(error));
    error = network_init();
    if (error != ESP_OK) event_log_append(EVENT_COMPONENT_FAILURE, 2, (uint32_t)error);
    indicators_init_results(error, modem_error);
    if (error != ESP_OK) ESP_LOGE("boot", "Network initialization failed: %s; TTL remains active", esp_err_to_name(error));
    error = uplink_init();
    if (error != ESP_OK) event_log_append(EVENT_COMPONENT_FAILURE, 3, (uint32_t)error);
    if (error != ESP_OK) ESP_LOGE("boot", "Uplink initialization failed: %s", esp_err_to_name(error));
    ESP_ERROR_CHECK(diagnostics_start());
    ESP_LOGI("boot", "TTL bring-up ready. Boot sends B2 queries only; no automatic device start.");
    ESP_LOGW("boot", "Wi-Fi/SmartConfig + LTE AT TCP bench adapter enabled; cloud TLS/authentication/OTA pending.");
}
