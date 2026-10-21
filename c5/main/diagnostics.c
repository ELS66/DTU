#include "diagnostics.h"
#include <inttypes.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "board.h"
#include "indicators.h"
#include "field_bus.h"
#include "runtime_store.h"
#include "modem.h"
#include "network.h"
#include "uplink.h"
#include "module_lte.h"
#include "supervision.h"
#include "board_cache.h"
#include "event_log.h"
#include "esp_app_desc.h"
#include "esp_netif_ip_addr.h"
#include "esp_console.h"
#include "esp_heap_caps.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static int events_report(uint64_t after, size_t limit, bool dump)
{
    module_events_page_t *page = malloc(sizeof(*page));
    if (!page) { printf("EVENTS out of memory\n"); return 1; }
    uint32_t tag;
    if (!event_log_page(after, limit, page, &tag)) { free(page); return 1; }
    printf("EVENTS boot=%08" PRIx32 " storage=RAM capacity=%u retained=%u oldest=%" PRIu64 " latest=%" PRIu64
           " overwritten=%" PRIu64 " rejected=%" PRIu32 " gap=%d cursor_ahead=%d\n",
           tag, MODULE_EVENTS_CAPACITY, (unsigned)page->retained, page->oldest, page->latest,
           page->overwritten, page->rejected, page->gap, page->cursor_ahead);
    if (dump) {
        for (size_t i = 0; i < page->count; ++i) {
            const module_event_t *e = &page->entries[i];
            printf("EVENT seq=%" PRIu64 " at=%" PRIu64 "ms code=%" PRIu32 " name=%s detail=%08" PRIx32 " value=%08" PRIx32 "\n",
                   e->sequence, e->uptime_ms, e->code, event_log_name(e->code), e->detail, e->value);
        }
        printf("EVENTS_END count=%u next=%" PRIu64 "\n", (unsigned)page->count, page->next_cursor);
    }
    bool ahead = page->cursor_ahead;
    free(page);
    return ahead ? 1 : 0;
}
static int events_command(int argc, char **argv)
{
    if (argc > 3) goto usage;
    uint64_t after = 0, limit = MODULE_EVENTS_PAGE_MAX;
    for (int i = 1; i < argc; ++i) {
        char *end;
        if (argv[i][0] < '0' || argv[i][0] > '9') goto usage;
        errno = 0;
        unsigned long long number = strtoull(argv[i], &end, 10);
        if (*end || errno == ERANGE) goto usage;
        if (i == 1) after = (uint64_t)number; else limit = (uint64_t)number;
    }
    if (!limit || limit > MODULE_EVENTS_PAGE_MAX) goto usage;
    return events_report(after, (size_t)limit, true);
usage:
    printf("events [after_sequence [1..16]] (read-only; follow next with the same boot tag, gap means overwritten history)\n");
    return 1;
}
static int cache_report(board_cache_kind_t kind, size_t offset, size_t count, bool dump)
{
    module_blob_t *snapshot = malloc(sizeof(*snapshot));
    if (!snapshot) { printf("CACHE out of memory\n"); return 1; }
    if (!board_cache_snapshot(kind, snapshot)) { free(snapshot); printf("CACHE unavailable\n"); return 1; }
    printf("CACHE %s known=%d storage=RAM format=%u revision=%" PRIu64 " source=%02X bytes=%u crc32=%08" PRIx32
           " observed=%" PRIu64 "ms event=%" PRIu64 "\n", kind == BOARD_CACHE_INFO ? "info" : "params", snapshot->known,
           snapshot->format_version, snapshot->revision, snapshot->source, (unsigned)snapshot->size,
           snapshot->crc32, snapshot->observed_ms, snapshot->content_event);
    if (dump && snapshot->known) {
        if (offset > snapshot->size) { free(snapshot); printf("offset exceeds cached length\n"); return 1; }
        if (count > snapshot->size - offset) count = snapshot->size - offset;
        printf("HEX offset=%u size=%u ", (unsigned)offset, (unsigned)count);
        for (size_t i = 0; i < count; ++i) printf("%02X", snapshot->bytes[offset+i]);
        printf("\n");
    }
    free(snapshot);
    return 0;
}
static int cache_command(int argc, char **argv)
{
    if (argc < 2 || argc > 4 || (strcmp(argv[1], "info") && strcmp(argv[1], "params"))) goto usage;
    unsigned long values[2] = {0, 64};
    for (int i = 2; i < argc; ++i) {
        char *end;
        if (argv[i][0] < '0' || argv[i][0] > '9') goto usage;
        values[i-2] = strtoul(argv[i], &end, 10);
        if (*end || values[i-2] > MODULE_PAYLOAD_MAX) goto usage;
    }
    if (!values[1] || values[1] > 256) goto usage;
    return cache_report(!strcmp(argv[1], "info") ? BOARD_CACHE_INFO : BOARD_CACHE_PARAMS, values[0], values[1], true);
usage:
    printf("cache info|params [offset [1..256 bytes]] (read-only RAM snapshot, default first 64 bytes)\n");
    return 1;
}
static int status_command(int argc, char **argv)
{
    (void)argc; (void)argv;
    runtime_status_t runtime;
    field_status_t field;
    runtime_get_status(&runtime);
    field_bus_get_status(&field);
    uint64_t uptime = (uint64_t)(esp_timer_get_time() / 1000);
    printf("hardware=V0.14.4 firmware=%s uptime=%" PRIu64 "ms heap=%u min_heap=%u\n",
           esp_app_get_description()->version, uptime, (unsigned)esp_get_free_heap_size(), (unsigned)esp_get_minimum_free_heap_size());
    events_report(0, 1, false);
    static const char *freshness[] = {"unknown", "fresh", "stale"};
    static const char *contact[] = {"not_started", "waiting", "online", "offline"};
    static const char *storage[] = {"starting", "unavailable", "ready", "read_degraded", "write_error", "sequence_exhausted"};
    if (runtime.live.known)
        printf("BOARD_STATE %s last_state=%u last_remaining=%us observation_age=%" PRIu64 "ms stale_after=%" PRIu64 "ms\n",
               freshness[runtime.freshness], runtime.live.state, runtime.live.remaining_seconds,
               uptime >= runtime.live.observed_uptime_ms ? uptime - runtime.live.observed_uptime_ms : 0,
               runtime_observation_timeout_ms());
    else printf("BOARD_STATE unknown (not initialized from historical snapshot)\n");
    printf("BOARD_CONTACT %s consecutive_timeout=%" PRIu32 " loss=%" PRIu32 " recovery=%" PRIu32
           " aborted=%" PRIu32 " last_valid_age=%" PRIi64 "ms offline_after=%" PRIu64 "ms\n", contact[field.contact_state],
           field.consecutive_timeouts, field.loss_events, field.recoveries, field.aborted_requests,
           field.ever_valid && uptime >= field.last_valid_ms ? (int64_t)(uptime - field.last_valid_ms) : -1,
           field_contact_timeout_ms());
    if (runtime.saved_valid)
        printf("HISTORY record=%" PRIu64 " boot=%08" PRIx32 " state=%u remaining=%us observed_uptime=%" PRIu64 "ms\n",
               runtime.saved.sequence, runtime.saved.boot_tag, runtime.saved.state,
               runtime.saved.remaining_seconds, runtime.saved.observed_uptime_ms);
    else printf("HISTORY none\n");
    printf("STORAGE %s available=%d init=%s write=%s ok=%" PRIu32 " failed=%" PRIu32
           " invalid_boot_slots=%" PRIu32 " saved_this_boot=%d\n",
           storage[runtime.storage_health], runtime.available, esp_err_to_name(runtime.init_error),
           esp_err_to_name(runtime.last_write_error), runtime.writes_ok, runtime.write_failures,
           runtime.invalid_boot_slots, runtime.saved_this_boot);
    printf("SNAPSHOT pending=%d blocked_stale=%d lagging=%d save_gap=%" PRIu64 "ms last_attempt=%" PRIu64
           "ms last_success=%" PRIu64 "ms retry_after=%" PRIu64 "ms reason=%d duplicate_event=%" PRIu32
           " merged_change=%" PRIu32 " rejected_observation=%" PRIu32 "\n",
           runtime.pending, runtime.blocked_stale, runtime.lagging, runtime.save_gap_ms,
           runtime.last_attempt_ms, runtime.last_success_ms, runtime.retry_after_ms, runtime.last_save_reason,
           runtime.duplicate_events, runtime.coalesced_changes, runtime.rejected_observations);
    printf("UART rx=%" PRIu32 " tx=%" PRIu32 " timeout=%" PRIu32 " checksum=%" PRIu32
           " length=%" PRIu32 " partial=%" PRIu32 " malformed=%" PRIu32 " unsolicited=%" PRIu32
           " overflow=%" PRIu32 " snapshot_fail=%" PRIu32 "\n",
           field.rx_frames, field.tx_frames, field.reply_timeouts, field.bad_checksums,
           field.bad_lengths, field.partial_timeouts, field.malformed, field.unsolicited,
           field.uart_overflows, runtime.write_failures);
    const module_uart_health_t *uart = &field.uart_health;
    printf("UART_HEALTH recovering=%d faults=%" PRIu32 " streak=%" PRIu32 " recovered=%" PRIu32
           " fifo=%" PRIu32 " buffer=%" PRIu32 " frame=%" PRIu32 " parity=%" PRIu32 " break=%" PRIu32
           " read=%" PRIu32 " queue_full=%" PRIu32 " pressure=%" PRIu32 " queue_peak=%" PRIu32
           " flags=%02" PRIx32 " last_fault=%" PRIu64 "ms guard_until=%" PRIu64 "ms flush_fail=%" PRIu32 " discarded_partial=%" PRIu32 "\n",
           uart->recovering, uart->fault_batches, uart->consecutive_faults, uart->recoveries, uart->fifo, uart->buffer,
           uart->frame, uart->parity, uart->breaks, uart->read_errors, uart->queue_full, uart->pressure_batches,
           uart->queue_peak, uart->last_flags, uart->last_fault_ms, uart->guard_until_ms, field.flush_failures, field.partial_discards);
    printf("CACHE_DIAG failures=%" PRIu32 " stale_param_reply=%" PRIu32 "\n", field.cache_failures, field.stale_param_replies);
    cache_report(BOARD_CACHE_INFO, 0, 0, false);
    cache_report(BOARD_CACHE_PARAMS, 0, 0, false);
    supervision_status_t supervision;
    supervision_get_status(&supervision);
    printf("WATCHDOG initialized=%d reset_reason=%d latched_mask=%02" PRIx32 " previous_valid=%d previous_mask=%02" PRIx32
           " previous_at=%" PRIu64 "ms hardware_timeout=5000ms\n", supervision.initialized, supervision.reset_reason,
           supervision.watch.fault_mask, supervision.previous_valid, supervision.previous_mask, supervision.previous_ms);
    for (unsigned i = 0; i < MODULE_WATCH_COUNT; ++i) {
        const module_watch_slot_t *s = &supervision.watch.slots[i];
        printf("TASK %s enabled=%d advances=%" PRIu32 " age=%" PRIi64 "ms budget=%" PRIu32 "ms\n",
               supervision_name(i), s->enabled, s->advances,
               s->enabled && uptime >= s->last_progress_ms ? (int64_t)(uptime - s->last_progress_ms) : -1, s->budget_ms);
    }
    network_status_t net;
    modem_status_t modem;
    network_get_status(&net);
    modem_get_status(&modem);
    esp_ip4_addr_t ip = {.addr = net.ipv4};
    printf("WIFI initialized=%d ipv4=" IPSTR " ready=%d channel=%u RSSI=%d reason=%u\n",
           net.initialized, IP2STR(&ip), net.wifi_ip, net.channel, net.rssi, net.disconnect_reason);
    printf("PROVISION active=%d candidate=%d saved=%d boot_decided=%d boot_action=%d drops=%" PRIu32
           " save_error=%s last_error=%s\n", net.provisioning, net.candidate, net.saved_credentials,
           net.boot_decided, net.boot_action, net.dropped_events,
           esp_err_to_name(net.save_error), esp_err_to_name(net.last_error));
    printf("MODEM started=%d AT=%d SIM=%d CME=%d power_pulsed=%d observation_age=%" PRIi64
           "ms timeouts=%" PRIu32 " uart_errors=%" PRIu32 "\n", modem.started, modem.at_ready,
           modem.sim, modem.last_cme, modem.power_pulsed,
           modem.observed_ms ? (int64_t)uptime - modem.observed_ms : -1,
           modem.timeouts, modem.uart_errors);
    printf("LTE model=%s revision=%s expected_model=%d registration=%u RSSI=%u attached=%d PDP=%d APN_match=%d IPv4=%s data_ready=%d\n",
           modem.model, modem.revision, modem.model_matches, modem.registration, modem.rssi,
           modem.attached, modem.pdp_active, modem.apn_matches, modem.pdp_ipv4, modem.data_ready);
    printf("LTE socket=%d session=%" PRIu32 " uncertain_send=%" PRIu32 " data_age=%" PRIi64 "ms\n",
           modem.socket_connected, modem.socket_session, modem.uncertain_sends,
           modem.data_observed_ms ? (int64_t)uptime - modem.data_observed_ms : -1);
    uplink_status_t uplink;
    uplink_get_status(&uplink);
    printf("UPLINK active=%d route=%d last_success=%d wifi_failure=%" PRIu32 " lte_failure=%" PRIu32
           " uncertain_write=%" PRIu32 " wifi_retry_after=%" PRIu64 "ms last_error=%s\n",
           uplink.active, uplink.route, uplink.last_success, uplink.wifi_failures, uplink.lte_failures,
           uplink.uncertain_writes, uplink.wifi_retry_after_ms, esp_err_to_name(uplink.last_error));
    printf("SIM: 0=unknown 1=absent 2=ready 3=locked; route: 0=none 1=wifi 2=LTE; boot: 0=wait 1=wifi 2=LTE 3=provision\n");
    printf("Wi-Fi/PDP/TCP are separate from authenticated cloud online. Plain TCP bench adapter only; cloud/TLS/OTA pending.\n");
    indicators_status_t lights;
    indicators_get_status(&lights);
    printf("LED mask=%02X auto=%02X override=%02X test=%d WIFI=%s LTE=%s UART_tx_bytes=%" PRIu64
           " UART_rx_bytes=%" PRIu64 " MQTT_connected=%d MQTT_link=%d\n",
           lights.lights.output_mask, lights.lights.automatic_mask, lights.lights.override_mask,
           lights.lights.test_active, module_indicator_phase_name(lights.lights.wifi),
           module_indicator_phase_name(lights.lights.lte), lights.tx_bytes, lights.rx_bytes,
           lights.mqtt_connected, lights.mqtt_link);
    return 0;
}
static int hex_value(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
static int device_command(int argc, char **argv)
{
    uint8_t command = 0, data[256] = {1};
    size_t size = 1;
    if (argc < 2) goto usage;
    if (!strcmp(argv[1], "state")) command = 0xb2;
    else if (!strcmp(argv[1], "type")) command = 0xb1;
    else if (!strcmp(argv[1], "params")) command = 0xb3;
    else if (!strcmp(argv[1], "stop")) command = 0xa2;
    else if (!strcmp(argv[1], "pause")) command = 0xa3;
    else if (!strcmp(argv[1], "resume")) command = 0xa4;
    else if (!strcmp(argv[1], "start") && argc == 3) {
        char *end = NULL;
        unsigned long seconds = strtoul(argv[2], &end, 10);
        if (!argv[2][0] || *end || seconds == 0 || seconds > 65535) goto usage;
        command = 0xa1; size = 2;
        data[0] = (uint8_t)(seconds >> 8); data[1] = (uint8_t)seconds;
    } else if (!strcmp(argv[1], "set") && argc == 3) {
        size_t chars = strlen(argv[2]);
        if (!chars || chars % 2 || chars / 2 > sizeof(data)) goto usage;
        command = 0xb4; size = chars / 2;
        for (size_t i = 0; i < size; ++i) {
            int hi = hex_value(argv[2][2 * i]), lo = hex_value(argv[2][2 * i + 1]);
            if (hi < 0 || lo < 0) goto usage;
            data[i] = (uint8_t)((hi << 4) | lo);
        }
    } else goto usage;
    if (command != 0xa1 && command != 0xb4 && argc != 2) goto usage;
    esp_err_t error = field_bus_request(command, data, size);
    printf("request %02X %s (queued does not mean executed)\n", command, esp_err_to_name(error));
    return error == ESP_OK ? 0 : 1;
usage:
    printf("device state|type|params|start <1..65535 seconds>|stop|pause|resume|set <hex_without_spaces>\n");
    return 1;
}
static int led_command(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "auto")) {
        indicators_auto(); printf("LED automatic display restored\n"); return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "test")) {
        indicators_test(); printf("LED test: 0..7, 250ms each, automatic return after 2s\n"); return 0;
    }
    if (argc != 3) goto usage;
    char *end;
    long index = strtol(argv[1], &end, 10);
    if (!argv[1][0] || *end || index < 0 || index > 7 ||
        (strcmp(argv[2], "on") && strcmp(argv[2], "off"))) goto usage;
    esp_err_t error = indicators_override((unsigned)index, !strcmp(argv[2], "on"));
    printf("LED override %s; expires in 5s\n", esp_err_to_name(error));
    return error == ESP_OK ? 0 : 1;
usage:
    printf("led <0..7> <on|off> (5s) | led test (2s sequential) | led auto\n");
    return 1;
}
typedef struct {
    uplink_mode_t mode;
    char host[128];
    uint16_t port;
    size_t size;
    uint8_t data[MODULE_LTE_CHUNK];
} probe_job_t;
static portMUX_TYPE probe_guard = portMUX_INITIALIZER_UNLOCKED;
static bool probe_running;
static void probe_task(void *context)
{
    probe_job_t *job = context;
    uint32_t token;
    esp_err_t error = uplink_open(job->mode, job->host, job->port, &token);
    if (error == ESP_OK) {
        uplink_status_t view;
        uplink_get_status(&view);
        printf("PROBE TCP connected via %s (no TLS/cloud authentication)\n", view.route == MODULE_LINK_WIFI ? "Wi-Fi" : "LTE");
        if (job->size) {
            error = uplink_write(token, job->data, job->size);
            uint8_t response[MODULE_LTE_CHUNK];
            size_t total = 0;
            int64_t deadline = esp_timer_get_time() / 1000 + 8000;
            while (error == ESP_OK && total < job->size) {
                int64_t remaining = deadline - esp_timer_get_time() / 1000;
                if (remaining <= 0) { error = ESP_ERR_TIMEOUT; break; }
                size_t received = 0;
                error = uplink_read(token, response + total, job->size - total, &received, (unsigned)remaining);
                total += received;
            }
            if (error == ESP_OK && memcmp(response, job->data, job->size)) error = ESP_ERR_INVALID_RESPONSE;
            printf("ECHO %s received=%u expected=%u; failure is not retried\n", esp_err_to_name(error), (unsigned)total, (unsigned)job->size);
        }
        esp_err_t close_error = uplink_close(token);
        if (close_error != ESP_OK) printf("PROBE cleanup: %s (connection may already have failed)\n", esp_err_to_name(close_error));
    } else printf("PROBE connect failed: %s; check status\n", esp_err_to_name(error));
    free(job);
    portENTER_CRITICAL(&probe_guard); probe_running = false; portEXIT_CRITICAL(&probe_guard);
    vTaskDelete(NULL);
}
static int network_command(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "provision")) {
        esp_err_t error = network_request_provision();
        printf("SmartConfig request %s; current Wi-Fi will disconnect. Use ESPTouch v1 in Android test app.\n", esp_err_to_name(error));
        return error == ESP_OK ? 0 : 1;
    }
    bool echo = argc == 6 && !strcmp(argv[1], "echo");
    if ((argc == 5 && !strcmp(argv[1], "probe")) || echo) {
        uplink_mode_t mode;
        if (!strcmp(argv[2], "auto")) mode = UPLINK_AUTO;
        else if (!strcmp(argv[2], "wifi")) mode = UPLINK_WIFI;
        else if (!strcmp(argv[2], "lte")) mode = UPLINK_LTE;
        else goto usage;
        char *end;
        unsigned long port = strtoul(argv[4], &end, 10);
        if (!argv[4][0] || *end || !port || port > 65535 || !module_lte_host_valid(argv[3])) goto usage;
        size_t size = echo ? strlen(argv[5])/2 : 0;
        if (echo && (!size || strlen(argv[5])%2 || size > MODULE_LTE_CHUNK)) goto usage;
        probe_job_t *job = calloc(1, sizeof(*job));
        if (!job) return 1;
        job->mode = mode; job->port = (uint16_t)port; job->size = size;
        snprintf(job->host, sizeof(job->host), "%s", argv[3]);
        for (size_t i = 0; i < size; ++i) {
            int hi = hex_value(argv[5][i*2]), lo = hex_value(argv[5][i*2+1]);
            if (hi < 0 || lo < 0) { free(job); goto usage; }
            job->data[i] = (uint8_t)((hi << 4) | lo);
        }
        portENTER_CRITICAL(&probe_guard);
        bool busy = probe_running;
        if (!busy) probe_running = true;
        portEXIT_CRITICAL(&probe_guard);
        if (busy) { free(job); printf("A network probe is already running\n"); return 1; }
        if (xTaskCreate(probe_task, "net_probe", 6144, job, 3, NULL) != pdPASS) {
            portENTER_CRITICAL(&probe_guard); probe_running = false; portEXIT_CRITICAL(&probe_guard);
            free(job); return 1;
        }
        printf("PROBE queued; use status while the background task connects\n");
        return 0;
    }
usage:
    printf("net provision | net probe <auto|wifi|lte> <host> <port> | net echo <auto|wifi|lte> <host> <port> <hex>\n");
    printf("probe connects only; echo sends explicit bench bytes to your TCP echo server. No cloud credentials.\n");
    return 1;
}
esp_err_t diagnostics_start(void)
{
    esp_err_t error = esp_console_register_help_command();
    if (error != ESP_OK) return error;
    const esp_console_cmd_t commands[] = {
        {.command="status", .help="Show live board state, historical snapshot and diagnostics", .func=status_command},
        {.command="device", .help="Read or explicitly control the TTL device; see device for syntax", .func=device_command},
        {.command="cache", .help="Read opaque board information/parameters in bounded HEX slices", .func=cache_command},
        {.command="events", .help="Page through bounded RAM fault/state records without clearing them", .func=events_command},
        {.command="led", .help="Timed per-lamp override, sequential self-test or automatic display", .func=led_command},
        {.command="net", .help="SmartConfig, TCP probe or explicit echo test; run net for syntax", .func=network_command},
    };
    for (unsigned i = 0; i < sizeof(commands) / sizeof(commands[0]); ++i) {
        error = esp_console_cmd_register(&commands[i]);
        if (error != ESP_OK) return error;
    }
    esp_console_repl_t *repl = NULL;
    esp_console_repl_config_t config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    config.prompt = "c5>";
    config.max_cmdline_length = 800;
    esp_console_dev_usb_serial_jtag_config_t usb = ESP_CONSOLE_DEV_USB_SERIAL_JTAG_CONFIG_DEFAULT();
    error = esp_console_new_repl_usb_serial_jtag(&usb, &config, &repl);
    return error == ESP_OK ? esp_console_start_repl(repl) : error;
}
