#pragma once
#include "esp_err.h"
#include "module_blob.h"
typedef enum { BOARD_CACHE_INFO, BOARD_CACHE_PARAMS, BOARD_CACHE_COUNT } board_cache_kind_t;
esp_err_t board_cache_init(void);
bool board_cache_observe(board_cache_kind_t kind, uint8_t command, const uint8_t *data,
                         size_t size, uint64_t now, uint64_t event_revision);
/* Snapshot includes the exact binary body, excluding a B1/B3 reply's result byte. */
bool board_cache_snapshot(board_cache_kind_t kind, module_blob_t *out);
