#ifndef MODULE_INDICATOR_H
#define MODULE_INDICATOR_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "network_policy.h"
typedef enum {
    MODULE_LED_WIFI_AMBER, MODULE_LED_WIFI_GREEN, MODULE_LED_WIFI_BLUE,
    MODULE_LED_LTE_AMBER, MODULE_LED_LTE_GREEN, MODULE_LED_LTE_BLUE,
    MODULE_LED_TX, MODULE_LED_RX, MODULE_LED_COUNT
} module_led_t;
typedef enum { INDICATOR_STARTING, INDICATOR_SEARCHING, INDICATOR_PROVISIONING,
               INDICATOR_VERIFYING, INDICATOR_READY, INDICATOR_NO_SIM,
               INDICATOR_REGISTERED, INDICATOR_FAULT } module_indicator_phase_t;
typedef struct {
    bool wifi_failed, wifi_initialized, provisioning, candidate, wifi_ip;
    bool lte_failed, lte_started, lte_at_ready, lte_model_mismatch;
    bool lte_sim_fresh, lte_registered, lte_registration_denied, lte_data_ready, lte_data_fresh;
    module_sim_t sim;
    bool mqtt_connected;
    module_link_t mqtt_link;
} module_indicator_inputs_t;
typedef struct {
    uint64_t tx_wire_end_ms, tx_until_ms, rx_until_ms, tx_bytes, rx_bytes;
    uint64_t override_until_ms[MODULE_LED_COUNT], test_start_ms;
    uint8_t override_values;
    bool test_requested;
    bool tx_submitting;
} module_indicator_t;
typedef struct {
    uint8_t automatic_mask, output_mask, override_mask;
    bool test_active;
    module_indicator_phase_t wifi, lte;
} module_indicator_output_t;
void module_indicator_tx(module_indicator_t *state, uint64_t now_ms, uint64_t queued_at_ms, size_t bytes);
void module_indicator_tx_begin(module_indicator_t *state);
void module_indicator_rx(module_indicator_t *state, uint64_t now_ms, size_t bytes);
bool module_indicator_override(module_indicator_t *state, unsigned led, bool on, uint64_t now_ms, unsigned ttl_ms);
void module_indicator_auto(module_indicator_t *state);
void module_indicator_test(module_indicator_t *state, uint64_t now_ms);
void module_indicator_render(const module_indicator_t *state, const module_indicator_inputs_t *inputs,
                             uint64_t now_ms, module_indicator_output_t *out);
const char *module_indicator_phase_name(module_indicator_phase_t phase);
#endif
