#include "network.h"
#include "supervision.h"
#include "event_log.h"
#include <string.h>
#include "board.h"
#include "modem.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_smartconfig.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nvs.h"
#include "sdkconfig.h"
typedef enum { NET_START, NET_STOP, NET_LINK, NET_DOWN, NET_IP, NET_LOST_IP,
               NET_CREDENTIALS, NET_ACK, NET_MANUAL } event_kind_t;
typedef struct {
    event_kind_t kind;
    uint16_t reason;
    uint32_t ip;
    smartconfig_event_got_ssid_pswd_t credentials;
} net_event_t;
/* Portable, versioned credential record; no SDK struct padding persisted. */
typedef struct { uint8_t version, ssid[32], password[64]; } credential_record_t;
static const char *TAG = "network";
static QueueHandle_t queue;
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static network_status_t status;
static nvs_handle_t storage;
static esp_netif_t *station;
static esp_event_handler_instance_t wifi_handler, ip_handler, sc_handler;
static int64_t now_ms(void) { return esp_timer_get_time() / 1000; }
void network_get_status(network_status_t *out)
{
    portENTER_CRITICAL(&lock); *out = status; portEXIT_CRITICAL(&lock);
}
static void event_handler(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    net_event_t event = {0};
    if (base == WIFI_EVENT) {
        switch (id) {
        case WIFI_EVENT_STA_START: event.kind = NET_START; break;
        case WIFI_EVENT_STA_STOP: event.kind = NET_STOP; break;
        case WIFI_EVENT_STA_CONNECTED: event.kind = NET_LINK; break;
        case WIFI_EVENT_STA_DISCONNECTED:
            event.kind = NET_DOWN;
            event.reason = ((wifi_event_sta_disconnected_t *)data)->reason;
            break;
        default: return;
        }
    } else if (base == IP_EVENT) {
        if (id == IP_EVENT_STA_GOT_IP) {
            ip_event_got_ip_t *ip = data;
            if (ip->esp_netif != station) return;
            event.kind = NET_IP; event.ip = ip->ip_info.ip.addr;
        } else if (id == IP_EVENT_STA_LOST_IP) event.kind = NET_LOST_IP;
        else return;
    } else if (base == SC_EVENT && id == SC_EVENT_GOT_SSID_PSWD) {
        event.kind = NET_CREDENTIALS;
        event.credentials = *(smartconfig_event_got_ssid_pswd_t *)data;
    } else if (base == SC_EVENT && id == SC_EVENT_SEND_ACK_DONE) event.kind = NET_ACK;
    else return;
    if (xQueueSend(queue, &event, 0) != pdPASS) {
        portENTER_CRITICAL(&lock); ++status.dropped_events; portEXIT_CRITICAL(&lock);
    }
    memset(&event.credentials, 0, sizeof(event.credentials));
}
esp_err_t network_request_provision(void)
{
    network_status_t view;
    network_get_status(&view);
    if (!view.initialized) return ESP_ERR_INVALID_STATE;
    net_event_t event = {.kind = NET_MANUAL};
    return xQueueSend(queue, &event, 0) == pdPASS ? ESP_OK : ESP_ERR_TIMEOUT;
}
static bool load_credentials(wifi_config_t *config)
{
    credential_record_t record = {0};
    size_t size = sizeof(record);
    esp_err_t error = nvs_get_blob(storage, "credentials", &record, &size);
    bool valid = error == ESP_OK && size == sizeof(record) && record.version == 1 && record.ssid[0];
    if (valid) {
        memcpy(config->sta.ssid, record.ssid, 32);
        memcpy(config->sta.password, record.password, 64);
    } else if (error != ESP_ERR_NVS_NOT_FOUND)
        ESP_LOGW(TAG, "Saved Wi-Fi record unavailable/invalid (%s); retained without erase", esp_err_to_name(error));
    memset(&record, 0, sizeof(record));
    return valid;
}
static esp_err_t save_credentials(const wifi_config_t *config)
{
    credential_record_t record = {.version = 1};
    memcpy(record.ssid, config->sta.ssid, 32);
    memcpy(record.password, config->sta.password, 64);
    esp_err_t error = nvs_set_blob(storage, "credentials", &record, sizeof(record));
    if (error == ESP_OK) error = nvs_commit(storage);
    memset(&record, 0, sizeof(record));
    return error;
}
static esp_err_t start_smartconfig(void)
{
    esp_err_t error = esp_smartconfig_set_type(SC_TYPE_ESPTOUCH);
    if (error != ESP_OK) return error;
    smartconfig_start_config_t config = SMARTCONFIG_START_CONFIG_DEFAULT();
    return esp_smartconfig_start(&config);
}
static esp_err_t start_configuration(const wifi_config_t *config)
{
    esp_err_t error = esp_wifi_set_config(WIFI_IF_STA, (wifi_config_t *)config);
    return error == ESP_OK ? esp_wifi_start() : error;
}
static void network_task(void *unused)
{
    (void)unused;
    network_status_t view = {.initialized = true};
    wifi_config_t saved = {0}, active = {0}, next = {0};
    bool have_saved = load_credentials(&saved), have_active = have_saved;
    bool started = false, linked = false, connecting = false, switching = false;
    bool candidate_verified = false, need_save = false, ack = false, start_sc_after_restart = false;
    bool cancel_pending = false;
    int64_t boot_deadline = now_ms() + CONFIG_MODULE_NETWORK_BOOT_MS;
    int64_t provision_deadline = 0, retry_at = 0, save_at = 0, connect_deadline = 0;
    uint32_t handled_drops = 0;
    module_boot_gate_t boot_gate = {0};
    int64_t switch_deadline = 0;
    active = saved;
    view.saved_credentials = have_saved;
    view.last_error = start_configuration(&active);
    if (view.last_error != ESP_OK) ESP_LOGE(TAG, "Wi-Fi start failed: %s", esp_err_to_name(view.last_error));
    for (;;) {
        net_event_t event = {0};
        bool received = xQueueReceive(queue, &event, pdMS_TO_TICKS(200)) == pdPASS;
        int64_t now = now_ms();
        bool request_sc = received && event.kind == NET_MANUAL;
        bool rollback = cancel_pending;
        network_status_t published;
        network_get_status(&published);
        if (published.dropped_events != handled_drops) {
            handled_drops = published.dropped_events;
            event_log_append(EVENT_NETWORK_DROPS, 0, handled_drops);
            /* Never save a candidate after losing the ordering of network events. */
            ESP_LOGE(TAG, "Network event overflow; cancel candidate and restore trusted configuration");
            view.boot_decided = true;
            boot_gate.closed = true;
            view.last_error = ESP_ERR_NO_MEM;
            rollback = true;
            received = false;
            request_sc = false;
        }
        if (received) switch (event.kind) {
        case NET_START:
            /* IDF 5.5.1 sets the C5 band after START, before any connect/SC request. */
            view.last_error = esp_wifi_set_band_mode(WIFI_BAND_MODE_AUTO);
            started = view.last_error == ESP_OK;
            connecting = false; retry_at = now;
            if (!started) {
                ESP_LOGE(TAG, "Dual-band setup failed: %s", esp_err_to_name(view.last_error));
                start_sc_after_restart = false;
                break;
            }
            if (start_sc_after_restart) {
                start_sc_after_restart = false;
                view.last_error = start_smartconfig();
                if (view.last_error == ESP_OK) {
                    view.provisioning = true;
                    provision_deadline = now + CONFIG_MODULE_PROVISION_MS;
                    ESP_LOGI(TAG, "PROVISION: open Espressif Android ESPTouch, select ESPTouch (v1), connect phone to target Wi-Fi");
                    ESP_LOGI(TAG, "Product mini-program entry/QR is not configured; future guide uses the same provisioning state");
                } else {
                    ESP_LOGE(TAG, "SmartConfig start failed: %s", esp_err_to_name(view.last_error));
                    rollback = true;
                }
            }
            break;
        case NET_STOP:
            started = linked = connecting = false;
            view.wifi_ip = false; view.ipv4 = 0; view.channel = 0;
            if (switching) {
                switching = false; active = next;
                have_active = active.sta.ssid[0] != 0;
                view.last_error = start_configuration(&active);
                if (view.last_error != ESP_OK) {
                    start_sc_after_restart = false;
                    ESP_LOGE(TAG, "Wi-Fi reconfiguration failed: %s", esp_err_to_name(view.last_error));
                }
            }
            break;
        case NET_LINK: linked = !switching && !start_sc_after_restart; break;
        case NET_DOWN:
            linked = connecting = false;
            view.wifi_ip = false; view.ipv4 = 0; view.channel = 0;
            view.disconnect_reason = event.reason;
            retry_at = now + 5000;
            break;
        case NET_LOST_IP:
            view.wifi_ip = false; view.ipv4 = 0;
            /* A station can retain association while DHCP expires. Reconnect explicitly. */
            if (!switching) esp_wifi_disconnect();
            break;
        case NET_IP: {
            wifi_ap_record_t ap = {0};
            size_t ssid_size = strnlen((const char *)active.sta.ssid, sizeof(active.sta.ssid));
            if (!linked || switching || !event.ip ||
                esp_wifi_sta_get_ap_info(&ap) != ESP_OK ||
                memcmp(ap.ssid, active.sta.ssid, ssid_size) || ap.ssid[ssid_size] ||
                (active.sta.bssid_set && memcmp(ap.bssid, active.sta.bssid, 6))) break;
            view.wifi_ip = true; view.ipv4 = event.ip; view.channel = ap.primary; view.rssi = ap.rssi;
            connecting = false;
            if (!view.boot_decided) {
                view.boot_action = module_network_boot_step(&boot_gate, MODULE_SIM_UNKNOWN, true, false);
                view.boot_decided = boot_gate.closed;
            }
            if (view.candidate && !candidate_verified) {
                candidate_verified = true; need_save = true; save_at = now;
            }
            ESP_LOGI(TAG, "Wi-Fi IPv4 acquired; channel=%u band=%s RSSI=%d. Cloud reachability not tested.",
                     ap.primary, ap.primary > 14 ? "5GHz" : "2.4GHz", ap.rssi);
            break;
        }
        case NET_CREDENTIALS:
            if (!view.provisioning || view.candidate || switching || !event.credentials.ssid[0]) break;
            memset(&next, 0, sizeof(next));
            memcpy(next.sta.ssid, event.credentials.ssid, 32);
            memcpy(next.sta.password, event.credentials.password, 64);
            next.sta.bssid_set = event.credentials.bssid_set;
            memcpy(next.sta.bssid, event.credentials.bssid, 6);
            view.candidate = true; candidate_verified = false; need_save = false;
            /* SC remains running to send its ACK. No old link exists: initial SC starts after STOP. */
            active = next; have_active = true; linked = connecting = false;
            view.wifi_ip = false; view.ipv4 = 0;
            view.last_error = esp_wifi_set_config(WIFI_IF_STA, &active);
            if (view.last_error == ESP_OK) {
                view.last_error = esp_wifi_connect();
                connecting = view.last_error == ESP_OK;
                connect_deadline = now + 20000;
            }
            if (view.last_error != ESP_OK) rollback = true;
            ESP_LOGI(TAG, "Candidate received; credentials hidden. Persist only after matching AP association and IPv4.");
            break;
        case NET_ACK: if (view.provisioning) ack = true; break;
        case NET_MANUAL: break;
        }
        memset(&event, 0, sizeof(event));
        if (!view.boot_decided && now >= boot_deadline) {
            modem_status_t modem;
            modem_get_status(&modem);
            module_sim_t sim = modem.at_ready && now - modem.observed_ms < 15000 ? modem.sim : MODULE_SIM_UNKNOWN;
            view.boot_action = module_network_boot_step(&boot_gate, sim, view.wifi_ip, true);
            view.boot_decided = boot_gate.closed;
            request_sc |= view.boot_action == MODULE_NET_PROVISION;
            if (view.boot_action == MODULE_NET_TRY_LTE)
                ESP_LOGI(TAG, "Boot: SIM ready, Wi-Fi unavailable; LTE registration/PDP monitored separately");
            else if (view.boot_action == MODULE_NET_WAIT)
                ESP_LOGW(TAG, "Boot: SIM unknown/locked; automatic provisioning suppressed; use status for diagnosis");
        }
        if (request_sc && !view.provisioning && !switching && !start_sc_after_restart) {
            view.boot_decided = true;
            boot_gate.closed = true;
            next = (wifi_config_t){0}; /* No association while SmartConfig scans. */
            start_sc_after_restart = true; switching = true;
            ack = candidate_verified = need_save = false; view.candidate = false;
            view.wifi_ip = false; view.ipv4 = 0; linked = connecting = false;
            view.last_error = esp_wifi_stop();
            switch_deadline = now + 5000;
            if (view.last_error == ESP_ERR_WIFI_NOT_STARTED) {
                switching = false; active = next; have_active = false;
                view.last_error = start_configuration(&active);
                if (view.last_error != ESP_OK) start_sc_after_restart = false;
            } else if (view.last_error != ESP_OK) {
                switching = start_sc_after_restart = false;
                ESP_LOGE(TAG, "Cannot enter SmartConfig: %s", esp_err_to_name(view.last_error));
            }
        }
        if (rollback) {
            cancel_pending = true;
            need_save = candidate_verified = false;
        }
        if (need_save && view.wifi_ip && now >= save_at) {
            view.save_error = save_credentials(&active);
            if (view.save_error == ESP_OK) {
                saved = active; saved.sta.bssid_set = false; have_saved = true;
                need_save = false; view.saved_credentials = true;
                ESP_LOGI(TAG, "Verified Wi-Fi configuration saved");
            } else {
                save_at = now + 5000;
                ESP_LOGE(TAG, "Wi-Fi persistence failed: %s; previous RAM backup retained", esp_err_to_name(view.save_error));
            }
        }
        if (view.provisioning && ((candidate_verified && ack) || now >= provision_deadline || rollback)) {
            view.last_error = esp_smartconfig_stop();
            if (view.last_error == ESP_OK) {
                view.provisioning = false;
                if (!candidate_verified) rollback = true;
                else { view.candidate = false; ESP_LOGI(TAG, "Provisioning ended; Wi-Fi candidate verified"); }
            } else ESP_LOGE(TAG, "SmartConfig stop failed: %s", esp_err_to_name(view.last_error));
        }
        if (rollback && !view.provisioning) {
            cancel_pending = false;
            start_sc_after_restart = false;
            view.candidate = candidate_verified = need_save = false;
            next = have_saved ? saved : (wifi_config_t){0};
            view.wifi_ip = false; view.ipv4 = 0; linked = connecting = false;
            switching = true;
            view.last_error = esp_wifi_stop();
            switch_deadline = now + 5000;
            if (view.last_error == ESP_ERR_WIFI_NOT_STARTED) {
                switching = false; active = next; have_active = have_saved;
                view.last_error = start_configuration(&active);
            } else if (view.last_error != ESP_OK) switching = false;
            ESP_LOGW(TAG, "Candidate abandoned; restoring previous saved Wi-Fi, no erase, no automatic provisioning loop");
        }
        if (switching && now >= switch_deadline) {
            /* Recover even when a STOP event was dropped. Candidate saving stays disabled. */
            view.last_error = esp_wifi_stop();
            switch_deadline = now + 5000;
            if (view.last_error == ESP_ERR_WIFI_NOT_STARTED) {
                switching = false; active = next; have_active = active.sta.ssid[0] != 0;
                view.last_error = start_configuration(&active);
                if (view.last_error != ESP_OK) start_sc_after_restart = false;
            }
        }
        if (started && connecting && !switching && !view.wifi_ip && now >= connect_deadline) {
            esp_wifi_disconnect();
            linked = connecting = false;
            retry_at = now + 5000;
        }
        if (started && have_active && !switching && !view.wifi_ip && !connecting && now >= retry_at) {
            view.last_error = esp_wifi_connect();
            connecting = view.last_error == ESP_OK;
            connect_deadline = now + 20000;
            retry_at = now + 5000;
        }
        portENTER_CRITICAL(&lock);
        view.dropped_events = status.dropped_events;
        status = view;
        portEXIT_CRITICAL(&lock);
        if (view.wifi_ip != published.wifi_ip)
            event_log_append(view.wifi_ip ? EVENT_WIFI_READY : EVENT_WIFI_DOWN, view.disconnect_reason, view.channel);
        if (view.provisioning != published.provisioning)
            event_log_append(view.provisioning ? EVENT_PROVISION_START : EVENT_PROVISION_END, view.candidate, 0);
        if (view.last_error != published.last_error && view.last_error != ESP_OK)
            event_log_append(EVENT_NETWORK_ERROR, (uint32_t)view.last_error, 0);
        if (view.save_error != published.save_error)
            event_log_append(EVENT_WIFI_SAVE_ERROR, (uint32_t)view.save_error, 0);
        supervision_progress(MODULE_WATCH_NETWORK);
    }
}
esp_err_t network_init(void)
{
    esp_err_t error = nvs_open("wifi_profile", NVS_READWRITE, &storage);
    if (error != ESP_OK) return error;
    error = esp_netif_init();
    if (error != ESP_OK) { nvs_close(storage); return error; }
    error = esp_event_loop_create_default();
    if (error != ESP_OK && error != ESP_ERR_INVALID_STATE) { nvs_close(storage); return error; }
    queue = xQueueCreate(24, sizeof(net_event_t));
    if (!queue) { nvs_close(storage); return ESP_ERR_NO_MEM; }
    station = esp_netif_create_default_wifi_sta();
    if (!station) { vQueueDelete(queue); queue = NULL; nvs_close(storage); return ESP_ERR_NO_MEM; }
    wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();
    bool initialized = false, wh = false, ih = false, sh = false;
    error = esp_wifi_init(&config);
    if (error != ESP_OK) goto fail;
    initialized = true;
    error = esp_wifi_set_storage(WIFI_STORAGE_RAM);
    if (error != ESP_OK) goto fail;
    error = esp_wifi_set_mode(WIFI_MODE_STA);
    if (error != ESP_OK) goto fail;
    error = esp_wifi_set_country_code(CONFIG_MODULE_WIFI_COUNTRY, true);
    if (error != ESP_OK) goto fail;
    error = esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, event_handler, NULL, &wifi_handler);
    if (error != ESP_OK) goto fail;
    wh = true;
    error = esp_event_handler_instance_register(IP_EVENT, ESP_EVENT_ANY_ID, event_handler, NULL, &ip_handler);
    if (error != ESP_OK) goto fail;
    ih = true;
    error = esp_event_handler_instance_register(SC_EVENT, ESP_EVENT_ANY_ID, event_handler, NULL, &sc_handler);
    if (error != ESP_OK) goto fail;
    sh = true;
    supervision_expect(MODULE_WATCH_NETWORK);
    if (xTaskCreate(network_task, "network", 6144, NULL, 4, NULL) == pdPASS) return ESP_OK;
    supervision_disable(MODULE_WATCH_NETWORK);
    error = ESP_ERR_NO_MEM;
fail:
    if (sh) esp_event_handler_instance_unregister(SC_EVENT, ESP_EVENT_ANY_ID, sc_handler);
    if (ih) esp_event_handler_instance_unregister(IP_EVENT, ESP_EVENT_ANY_ID, ip_handler);
    if (wh) esp_event_handler_instance_unregister(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_handler);
    if (initialized) esp_wifi_deinit();
    esp_netif_destroy_default_wifi(station); station = NULL;
    vQueueDelete(queue); queue = NULL;
    nvs_close(storage);
    return error;
}
