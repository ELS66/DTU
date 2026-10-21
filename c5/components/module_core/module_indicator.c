#include "module_indicator.h"
#include <string.h>
#define LED(id) ((uint8_t)(1u << (id)))
void module_indicator_tx_begin(module_indicator_t *s) { s->tx_submitting = true; }
void module_indicator_tx(module_indicator_t *s, uint64_t now, uint64_t queued_at, size_t bytes)
{
    s->tx_submitting = false;
    if (!bytes) return;
    uint64_t base = s->tx_wire_end_ms > queued_at ? s->tx_wire_end_ms : queued_at;
    s->tx_wire_end_ms = base + ((uint64_t)bytes * 10000 + 9599) / 9600;
    s->tx_until_ms = (s->tx_wire_end_ms > now ? s->tx_wire_end_ms : now) + 75;
    s->tx_bytes += bytes;
}
void module_indicator_rx(module_indicator_t *s, uint64_t now, size_t bytes)
{
    if (!bytes) return;
    s->rx_until_ms = now + 75;
    s->rx_bytes += bytes;
}
void module_indicator_auto(module_indicator_t *s)
{
    memset(s->override_until_ms, 0, sizeof(s->override_until_ms));
    s->override_values = 0;
    s->test_requested = false;
}
bool module_indicator_override(module_indicator_t *s, unsigned led, bool on, uint64_t now, unsigned ttl)
{
    if (led >= MODULE_LED_COUNT || !ttl || ttl > 60000) return false;
    s->test_requested = false;
    s->override_until_ms[led] = now + ttl;
    if (on) s->override_values |= LED(led);
    else s->override_values &= (uint8_t)~LED(led);
    return true;
}
void module_indicator_test(module_indicator_t *s, uint64_t now)
{
    module_indicator_auto(s);
    s->test_requested = true; s->test_start_ms = now;
}
void module_indicator_render(const module_indicator_t *s, const module_indicator_inputs_t *i,
                             uint64_t now, module_indicator_output_t *o)
{
    memset(o, 0, sizeof(*o));
    bool slow = now % 2000 < 1000, search = now % 1000 < 500, fast = now % 250 < 125;
    bool wifi_ready = i->wifi_initialized && !i->wifi_failed && i->wifi_ip;
    bool lte_ready = i->lte_started && !i->lte_failed && i->lte_at_ready && !i->lte_model_mismatch &&
                     i->lte_sim_fresh && i->sim == MODULE_SIM_PRESENT && i->lte_registered && !i->lte_registration_denied &&
                     i->lte_data_ready && i->lte_data_fresh;
    bool amber = false;
    if (i->wifi_failed) { o->wifi = INDICATOR_FAULT; amber = fast; }
    else if (i->provisioning) {
        o->wifi = i->candidate ? INDICATOR_VERIFYING : INDICATOR_PROVISIONING;
        amber = i->candidate ? fast : search;
    } else if (wifi_ready) o->wifi = INDICATOR_READY;
    else if (!i->wifi_initialized) { o->wifi = INDICATOR_STARTING; amber = slow; }
    else { o->wifi = INDICATOR_SEARCHING; amber = slow; }
    if (amber) o->automatic_mask |= LED(MODULE_LED_WIFI_AMBER);
    if (wifi_ready) o->automatic_mask |= LED(MODULE_LED_WIFI_GREEN);
    if (wifi_ready && !i->provisioning && i->mqtt_connected && i->mqtt_link == MODULE_LINK_WIFI)
        o->automatic_mask |= LED(MODULE_LED_WIFI_BLUE);
    amber = false;
    if (i->lte_failed || (i->lte_at_ready && i->lte_model_mismatch) ||
        (i->lte_sim_fresh && (i->sim == MODULE_SIM_LOCKED || i->lte_registration_denied))) {
        o->lte = INDICATOR_FAULT; amber = fast;
    } else if (!i->lte_started) { o->lte = INDICATOR_STARTING; amber = slow; }
    else if (!i->lte_at_ready || !i->lte_sim_fresh || i->sim == MODULE_SIM_UNKNOWN) {
        o->lte = INDICATOR_SEARCHING; amber = search;
    } else if (i->sim == MODULE_SIM_ABSENT) {
        uint64_t phase = now % 2000;
        o->lte = INDICATOR_NO_SIM; amber = phase < 100 || (phase >= 200 && phase < 300);
    } else if (lte_ready) {
        o->lte = INDICATOR_READY; o->automatic_mask |= LED(MODULE_LED_LTE_GREEN);
    } else if (i->lte_registered && i->sim == MODULE_SIM_PRESENT) {
        o->lte = INDICATOR_REGISTERED;
        if (search) o->automatic_mask |= LED(MODULE_LED_LTE_GREEN);
    } else { o->lte = INDICATOR_SEARCHING; amber = search; }
    if (amber) o->automatic_mask |= LED(MODULE_LED_LTE_AMBER);
    if (lte_ready && i->mqtt_connected && i->mqtt_link == MODULE_LINK_LTE)
        o->automatic_mask |= LED(MODULE_LED_LTE_BLUE);
    if (s->tx_submitting || now < s->tx_until_ms) o->automatic_mask |= LED(MODULE_LED_TX);
    if (now < s->rx_until_ms) o->automatic_mask |= LED(MODULE_LED_RX);
    o->output_mask = o->automatic_mask;
    for (unsigned led = 0; led < MODULE_LED_COUNT; ++led) {
        if (now < s->override_until_ms[led]) {
            o->override_mask |= LED(led);
            o->output_mask = (uint8_t)((o->output_mask & ~LED(led)) | (s->override_values & LED(led)));
        }
    }
    if (s->test_requested && now >= s->test_start_ms && now - s->test_start_ms < MODULE_LED_COUNT * 250) {
        o->test_active = true;
        o->output_mask = LED((now - s->test_start_ms) / 250);
    }
}
const char *module_indicator_phase_name(module_indicator_phase_t phase)
{
    static const char *names[] = {"starting", "searching", "provisioning", "verifying",
                                 "ready", "no_sim", "registered", "fault"};
    return (unsigned)phase < sizeof(names)/sizeof(names[0]) ? names[phase] : "unknown";
}
