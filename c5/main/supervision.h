#pragma once
#include "esp_err.h"
#include "module_supervision.h"
typedef struct {
    bool initialized, previous_valid;
    int reset_reason;
    uint32_t previous_mask;
    uint64_t previous_ms;
    module_watch_t watch;
} supervision_status_t;
esp_err_t supervision_init(void);
void supervision_expect(module_watch_id_t id);
void supervision_disable(module_watch_id_t id);
void supervision_progress(module_watch_id_t id);
void supervision_get_status(supervision_status_t *status);
const char *supervision_name(unsigned id);
