#include "board_cache.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
static SemaphoreHandle_t lock;
static module_blob_t values[BOARD_CACHE_COUNT];
esp_err_t board_cache_init(void)
{
    lock = xSemaphoreCreateMutex();
    return lock ? ESP_OK : ESP_ERR_NO_MEM;
}
bool board_cache_observe(board_cache_kind_t kind, uint8_t command, const uint8_t *data,
                         size_t size, uint64_t now, uint64_t event)
{
    if ((unsigned)kind >= BOARD_CACHE_COUNT || !lock ||
        (kind == BOARD_CACHE_INFO ? command != 0xb1 : (command != 0xb3 && command != 0xc5)) ||
        xSemaphoreTake(lock, pdMS_TO_TICKS(50)) != pdTRUE) return false;
    module_blob_result_t result = module_blob_update(&values[kind], command, data, size, now, event);
    xSemaphoreGive(lock);
    return result != MODULE_BLOB_REJECTED;
}
bool board_cache_snapshot(board_cache_kind_t kind, module_blob_t *out)
{
    if ((unsigned)kind >= BOARD_CACHE_COUNT || !out || !lock || xSemaphoreTake(lock, pdMS_TO_TICKS(50)) != pdTRUE) return false;
    *out = values[kind];
    xSemaphoreGive(lock);
    return true;
}
