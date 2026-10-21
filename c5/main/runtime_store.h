#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "module_record.h"
#include "module_runtime_policy.h"
typedef module_observation_t device_observation_t;
typedef enum { RUNTIME_STORAGE_STARTING, RUNTIME_STORAGE_UNAVAILABLE, RUNTIME_STORAGE_READY,
               RUNTIME_STORAGE_READ_DEGRADED, RUNTIME_STORAGE_WRITE_ERROR,
               RUNTIME_STORAGE_SEQUENCE_EXHAUSTED } runtime_storage_health_t;
typedef struct {
    device_observation_t live;
    bool saved_valid;
    module_record_t saved;
    uint32_t write_failures;
    bool init_attempted, available, saved_this_boot, pending, lagging, blocked_stale;
    bool sequence_exhausted;
    uint32_t writes_ok, invalid_boot_slots, rejected_observations;
    uint32_t duplicate_events, coalesced_changes;
    uint64_t last_attempt_ms, last_success_ms, retry_after_ms, save_gap_ms;
    esp_err_t init_error, last_write_error;
    module_state_freshness_t freshness;
    runtime_storage_health_t storage_health;
    module_save_reason_t last_save_reason;
} runtime_status_t;
esp_err_t runtime_store_init(void);
void runtime_observe(uint8_t command, uint8_t state, uint16_t remaining, bool urgent);
void runtime_get_status(runtime_status_t *status);
uint64_t runtime_observation_timeout_ms(void);
