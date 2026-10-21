#include "indicators.h"
#include "supervision.h"
#include "board.h"
#include "network.h"
#include "modem.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static module_indicator_t state;
static indicators_status_t status;
static bool wifi_failed, lte_failed, mqtt_connected;
static module_link_t mqtt_link;
static uint64_t now_ms(void) { return (uint64_t)(esp_timer_get_time() / 1000); }
void indicators_get_status(indicators_status_t *out)
{
    portENTER_CRITICAL(&lock); *out = status; portEXIT_CRITICAL(&lock);
}
void indicators_init_results(esp_err_t wifi, esp_err_t lte)
{
    portENTER_CRITICAL(&lock); wifi_failed = wifi != ESP_OK; lte_failed = lte != ESP_OK; portEXIT_CRITICAL(&lock);
}
void indicators_tx(size_t bytes, uint64_t queued_at_ms)
{
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock); module_indicator_tx(&state, now, queued_at_ms, bytes); portEXIT_CRITICAL(&lock);
}
void indicators_tx_begin(void)
{
    portENTER_CRITICAL(&lock); module_indicator_tx_begin(&state); portEXIT_CRITICAL(&lock);
}
void indicators_rx(size_t bytes)
{
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock); module_indicator_rx(&state, now, bytes); portEXIT_CRITICAL(&lock);
}
esp_err_t indicators_override(unsigned index, bool on)
{
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock);
    bool valid = module_indicator_override(&state, index, on, now, 5000);
    portEXIT_CRITICAL(&lock);
    return valid ? ESP_OK : ESP_ERR_INVALID_ARG;
}
void indicators_auto(void)
{
    portENTER_CRITICAL(&lock); module_indicator_auto(&state); portEXIT_CRITICAL(&lock);
}
void indicators_test(void)
{
    uint64_t now = now_ms();
    portENTER_CRITICAL(&lock); module_indicator_test(&state, now); portEXIT_CRITICAL(&lock);
}
void indicators_mqtt_state(module_link_t link, bool connected)
{
    if (connected && link != MODULE_LINK_WIFI && link != MODULE_LINK_LTE) return;
    portENTER_CRITICAL(&lock);
    if (connected || link == MODULE_LINK_NONE || link == mqtt_link) {
        mqtt_connected = connected; mqtt_link = connected ? link : MODULE_LINK_NONE;
    }
    portEXIT_CRITICAL(&lock);
}
static void indicator_task(void *unused)
{
    (void)unused;
    TickType_t wake = xTaskGetTickCount();
    uint8_t previous = 0;
    for (;;) {
        uint64_t now = now_ms();
        network_status_t wifi;
        modem_status_t lte;
        network_get_status(&wifi); modem_get_status(&lte);
        module_indicator_inputs_t inputs = {
            .wifi_initialized = wifi.initialized, .wifi_ip = wifi.wifi_ip,
            .provisioning = wifi.provisioning, .candidate = wifi.candidate,
            .lte_started = lte.started, .lte_at_ready = lte.at_ready,
            .lte_model_mismatch = lte.model[0] && !lte.model_matches,
            .lte_sim_fresh = lte.observed_ms > 0 && now >= (uint64_t)lte.observed_ms && now - lte.observed_ms < 15000,
            .sim = lte.sim, .lte_registered = lte.registration == 1 || lte.registration == 5,
            .lte_registration_denied = lte.registration == 3, .lte_data_ready = lte.data_ready,
            .lte_data_fresh = lte.data_observed_ms > 0 && now >= (uint64_t)lte.data_observed_ms && now - lte.data_observed_ms < 20000,
        };
        portENTER_CRITICAL(&lock);
        inputs.wifi_failed = wifi_failed; inputs.lte_failed = lte_failed;
        bool wifi_usable = !wifi_failed && inputs.wifi_initialized && inputs.wifi_ip && !inputs.provisioning;
        bool lte_usable = !lte_failed && inputs.lte_started && inputs.lte_at_ready &&
                          !inputs.lte_model_mismatch && inputs.lte_sim_fresh && inputs.sim == MODULE_SIM_PRESENT &&
                          inputs.lte_registered && !inputs.lte_registration_denied && inputs.lte_data_ready && inputs.lte_data_fresh;
        if (mqtt_connected && ((mqtt_link == MODULE_LINK_WIFI && !wifi_usable) ||
                               (mqtt_link == MODULE_LINK_LTE && !lte_usable))) {
            mqtt_connected = false; mqtt_link = MODULE_LINK_NONE;
        }
        inputs.mqtt_connected = mqtt_connected; inputs.mqtt_link = mqtt_link;
        module_indicator_render(&state, &inputs, now, &status.lights);
        status.tx_bytes = state.tx_bytes; status.rx_bytes = state.rx_bytes;
        status.mqtt_connected = mqtt_connected; status.mqtt_link = mqtt_link;
        uint8_t mask = status.lights.output_mask;
        portEXIT_CRITICAL(&lock);
        if (mask != previous) { board_apply_led_mask(mask); previous = mask; }
        supervision_progress(MODULE_WATCH_LED);
        xTaskDelayUntil(&wake, pdMS_TO_TICKS(20));
    }
}
esp_err_t indicators_init(void)
{
    supervision_expect(MODULE_WATCH_LED);
    if (xTaskCreate(indicator_task, "indicators", 4096, NULL, 3, NULL) == pdPASS) return ESP_OK;
    supervision_disable(MODULE_WATCH_LED);
    return ESP_ERR_NO_MEM;
}
