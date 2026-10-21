#pragma once
#include "esp_err.h"
#include "module_indicator.h"
typedef struct {
    module_indicator_output_t lights;
    uint64_t tx_bytes, rx_bytes;
    bool mqtt_connected;
    module_link_t mqtt_link;
} indicators_status_t;
esp_err_t indicators_init(void);
void indicators_init_results(esp_err_t wifi, esp_err_t lte);
void indicators_tx(size_t bytes, uint64_t queued_at_ms);
void indicators_tx_begin(void);
void indicators_rx(size_t bytes);
esp_err_t indicators_override(unsigned index, bool on);
void indicators_auto(void);
void indicators_test(void);
/* Future MQTT client must report real connect/disconnect; TCP probe never calls this. */
void indicators_mqtt_state(module_link_t link, bool connected);
void indicators_get_status(indicators_status_t *out);
