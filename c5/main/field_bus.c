#include "field_bus.h"
#include <string.h>
#include <stdlib.h>
#include "board.h"
#include "indicators.h"
#include "runtime_store.h"
#include "supervision.h"
#include "board_cache.h"
#include "event_log.h"
#include "module_protocol.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "sdkconfig.h"

static const char *TAG = "field";
static const uart_port_t PORT = UART_NUM_0;
typedef struct { size_t size; uint8_t frame[MODULE_FRAME_MAX]; } request_t;
static QueueHandle_t requests, uart_events;
static module_parser_t parser;
static request_t outgoing;
static field_status_t counters;
static portMUX_TYPE counter_lock = portMUX_INITIALIZER_UNLOCKED;
static uint8_t pending_command;
static int64_t reply_deadline, guard_until, next_poll;
static uint64_t board_event_revision, pending_event_revision;
static uint64_t params_event_revision, pending_params_revision;
#define UART_QUEUE_CAPACITY 16u
static module_peer_t peer;
uint64_t field_contact_timeout_ms(void)
{
    return module_contact_timeout_ms(runtime_observation_timeout_ms(), CONFIG_MODULE_STATUS_POLL_MS, CONFIG_MODULE_REPLY_TIMEOUT_MS);
}

static uint16_t be16(const uint8_t *p) { return (uint16_t)(((uint16_t)p[0] << 8) | p[1]); }
static void count(uint32_t *counter)
{
    portENTER_CRITICAL(&counter_lock);
    ++*counter;
    portEXIT_CRITICAL(&counter_lock);
}
void field_bus_get_status(field_status_t *output)
{
    portENTER_CRITICAL(&counter_lock);
    *output = counters;
    module_peer_t current_peer = peer;
    portEXIT_CRITICAL(&counter_lock);
    output->contact_state = module_peer_state(&current_peer, (uint64_t)(esp_timer_get_time() / 1000), field_contact_timeout_ms());
    output->ever_valid = current_peer.ever_valid;
    output->last_valid_ms = current_peer.last_valid_ms;
    output->consecutive_timeouts = current_peer.consecutive_timeouts;
    output->loss_events = current_peer.loss_events;
    output->recoveries = current_peer.recoveries;
}
static void contact_received(bool reply)
{
    uint64_t now = (uint64_t)(esp_timer_get_time() / 1000);
    portENTER_CRITICAL(&counter_lock);
    uint32_t before = peer.recoveries;
    uint32_t before_loss = peer.loss_events;
    module_peer_received(&peer, now, field_contact_timeout_ms(), reply);
    bool recovered = peer.recoveries != before;
    bool lost = peer.loss_events != before_loss;
    bool uart_recovered = module_uart_good(&counters.uart_health, now);
    portEXIT_CRITICAL(&counter_lock);
    if (lost) event_log_append(EVENT_BOARD_OFFLINE, 0, 0);
    if (recovered) event_log_append(EVENT_BOARD_RECOVERED, reply, 0);
    if (uart_recovered) event_log_append(EVENT_UART_RECOVERED, 0, 0);
    if (recovered) ESP_LOGI(TAG, "Board contact recovered; state freshness follows accepted state observations");
    if (uart_recovered) ESP_LOGI(TAG, "Field UART recovered after guard and validated board traffic");
}
static bool transmit(const uint8_t *bytes, size_t size)
{
    uint64_t queued_at = (uint64_t)(esp_timer_get_time() / 1000);
    indicators_tx_begin();
    int written = uart_write_bytes(PORT, bytes, size);
    indicators_tx(written > 0 ? (size_t)written : 0, queued_at);
    if (written != (int)size) {
        event_log_append(EVENT_UART_TX_FAILURE, 0, (uint32_t)size);
        ESP_LOGE(TAG, "UART send failed");
        return false;
    }
    count(&counters.tx_frames);
    ESP_LOG_BUFFER_HEX_LEVEL(TAG, bytes, size > 64 ? 64 : size, ESP_LOG_DEBUG);
    return true;
}
static void acknowledge(uint8_t command, uint8_t result)
{
    uint8_t bytes[8];
    size_t size = module_encode(command, &result, 1, bytes, sizeof(bytes));
    transmit(bytes, size);
}
static void receive_frame(void *context, const module_frame_t *f)
{
    (void)context;
    count(&counters.rx_frames);
    ESP_LOGD(TAG, "RX command=%02X payload=%u", f->command, (unsigned)f->size);
    ESP_LOG_BUFFER_HEX_LEVEL(TAG, f->data, f->size > 64 ? 64 : f->size, ESP_LOG_DEBUG);
    if (module_is_event(f->command)) {
        if ((f->command == 0xc1 && (f->size != 1 || f->data[0] != 1)) ||
            ((f->command >= 0xc2 && f->command <= 0xc4) && f->size != 2) ||
            (f->command == 0xc7 && (f->size != 1 || f->data[0] != 1))) {
            count(&counters.malformed);
            acknowledge(f->command, 0);
            return;
        }
        if (f->command == 0xc7) {
            contact_received(false);
            /* Identity/QR is not configured in this first bring-up firmware. */
            count(&counters.unsupported_events);
            acknowledge(f->command, 2);
            ESP_LOGW(TAG, "C7 QR response not configured (returned UNSUPPORTED)");
            return;
        }
        contact_received(false);
        if (f->command >= 0xc1 && f->command <= 0xc4) ++board_event_revision;
        if (f->command == 0xc1) runtime_observe(f->command, 0, 0, true);
        if (f->command >= 0xc2 && f->command <= 0xc4) {
            uint8_t state = f->command == 0xc2 ? 1 : f->command == 0xc3 ? 3 : 0;
            runtime_observe(f->command, state, be16(f->data), true);
        }
        if (f->command == 0xc5) {
            if (params_event_revision == UINT64_MAX ||
                !board_cache_observe(BOARD_CACHE_PARAMS, f->command, f->data, f->size,
                                     (uint64_t)(esp_timer_get_time() / 1000), ++params_event_revision)) {
                count(&counters.cache_failures);
                event_log_append(EVENT_CACHE_FAILURE, f->command, (uint32_t)f->size);
                acknowledge(f->command, 0);
                return;
            }
        }
        /* C5 acknowledges a RAM cache update, not durable cloud delivery. */
        acknowledge(f->command, 1);
        ESP_LOGI(TAG, "Board event %02X: %u bytes acknowledged", f->command, (unsigned)f->size);
        return;
    }
    int64_t now = esp_timer_get_time() / 1000;
    if (!pending_command || pending_command != f->command || now >= reply_deadline) {
        count(&counters.unsolicited);
        return;
    }
    if (!f->size || f->data[0] > 2) {
        count(&counters.malformed);
        return;
    }
    if (f->data[0] == 1) {
        bool time_reply = f->command >= 0xa2 && f->command <= 0xa4;
        if ((time_reply && f->size != 3) || (f->command == 0xb2 &&
            (f->size != 4 || !module_work_state_valid(f->data[1])))) {
            count(&counters.malformed);
            return;
        }
        /* A panel event after the request can make this response stale. Query again. */
        bool current = pending_event_revision == board_event_revision;
        if (!current) next_poll = now;
        if (f->command == 0xb2 && current)
            runtime_observe(f->command, f->data[1], be16(f->data + 2), false);
        if (time_reply && current) {
            uint8_t state = f->command == 0xa2 ? 0 : f->command == 0xa3 ? 3 : 1;
            runtime_observe(f->command, state, be16(f->data + 1), true);
        }
        if (f->command == 0xb1 || f->command == 0xb3) {
            bool latest = f->command == 0xb1 || (params_event_revision != UINT64_MAX &&
                module_blob_query_current(pending_params_revision, params_event_revision));
            if (!latest) {
                count(&counters.stale_param_replies);
                event_log_append(EVENT_STALE_PARAM_REPLY, f->command, 0);
            }
            else if (!board_cache_observe(f->command == 0xb1 ? BOARD_CACHE_INFO : BOARD_CACHE_PARAMS,
                                         f->command, f->data + 1, f->size - 1, (uint64_t)now,
                                         f->command == 0xb1 ? 0 : params_event_revision)) {
                count(&counters.cache_failures);
                event_log_append(EVENT_CACHE_FAILURE, f->command, (uint32_t)(f->size - 1));
            }
        }
    }
    contact_received(true);
    if (f->command != 0xb2 || f->data[0] != 1)
        ESP_LOGI(TAG, "Reply %02X status=%u payload=%u", f->command, f->data[0], (unsigned)f->size);
    pending_command = 0;
    /* A1 only acknowledges acceptance; B2 establishes actual remaining time. */
    if (f->command >= 0xa1 && f->command <= 0xa4) next_poll = now;
}
esp_err_t field_bus_request(uint8_t command, const uint8_t *data, size_t size)
{
    if (!requests || !module_is_request(command)) return ESP_ERR_INVALID_STATE;
    if (size > MODULE_PAYLOAD_MAX || (size && !data)) return ESP_ERR_INVALID_ARG;
    /* Keep large command buffers off the USB console task stack. */
    request_t *request = malloc(sizeof(*request));
    if (!request) return ESP_ERR_NO_MEM;
    request->size = module_encode(command, data, size, request->frame, sizeof(request->frame));
    BaseType_t queued = xQueueSend(requests, request, 0);
    free(request);
    return queued == pdTRUE ? ESP_OK : ESP_ERR_TIMEOUT;
}
static uint32_t collect_uart_faults(void)
{
    unsigned queued = uxQueueMessagesWaiting(uart_events);
    portENTER_CRITICAL(&counter_lock);
    bool full = module_uart_pressure(&counters.uart_health, queued, UART_QUEUE_CAPACITY);
    portEXIT_CRITICAL(&counter_lock);
    uint32_t flags = full ? MODULE_UART_QUEUE_FULL : 0;
    uart_event_t event;
    /* Bound event work even when the ISR keeps producing notifications. */
    for (unsigned i = 0; i < UART_QUEUE_CAPACITY * 2 && xQueueReceive(uart_events, &event, 0) == pdTRUE; ++i) {
        if (event.type == UART_FIFO_OVF) flags |= MODULE_UART_FIFO;
        if (event.type == UART_BUFFER_FULL) flags |= MODULE_UART_BUFFER;
        if (event.type == UART_FRAME_ERR) flags |= MODULE_UART_FRAME;
        if (event.type == UART_PARITY_ERR) flags |= MODULE_UART_PARITY;
        if (event.type == UART_BREAK) flags |= MODULE_UART_BREAK;
    }
    return flags;
}
static void recover_uart(uint32_t flags, int64_t now)
{
    size_t buffered = 0;
    if (uart_get_buffered_data_len(PORT, &buffered) == ESP_OK && buffered) indicators_rx(buffered);
    if (uart_flush_input(PORT) != ESP_OK) count(&counters.flush_failures);
    module_parser_discard(&parser);
    if (pending_command) count(&counters.aborted_requests);
    pending_command = 0;
    guard_until = now + CONFIG_MODULE_QUERY_GUARD_MS;
    portENTER_CRITICAL(&counter_lock);
    bool first = !counters.uart_health.recovering;
    module_uart_fault(&counters.uart_health, flags, (uint64_t)now, CONFIG_MODULE_QUERY_GUARD_MS);
    if (flags & (MODULE_UART_FIFO | MODULE_UART_BUFFER)) ++counters.uart_overflows;
    portEXIT_CRITICAL(&counter_lock);
    /* One log per fault episode; repeated errors remain visible through counters. */
    if (first) event_log_append(EVENT_UART_FAULT, flags, 0);
    if (first) ESP_LOGW(TAG, "UART data untrusted flags=0x%02lx; discarded RX, canceled pending request, no control replay",
                       (unsigned long)flags);
}
static void field_task(void *argument)
{
    (void)argument;
    uint8_t bytes[256];
    int64_t last_rx = 0;
    while (true) {
        supervision_progress(MODULE_WATCH_FIELD);
        uint32_t faults = collect_uart_faults();
        int length = uart_read_bytes(PORT, bytes, sizeof(bytes), pdMS_TO_TICKS(20));
        int64_t now = esp_timer_get_time() / 1000;
        if (length > 0) indicators_rx((size_t)length);
        faults |= collect_uart_faults(); /* Include errors arriving while uart_read_bytes waited. */
        if (length < 0) faults |= MODULE_UART_READ;
        if (faults) { recover_uart(faults, now); length = 0; }
        portENTER_CRITICAL(&counter_lock);
        uint32_t before_loss = peer.loss_events;
        module_peer_tick(&peer, (uint64_t)now, field_contact_timeout_ms());
        bool lost = peer.loss_events != before_loss;
        portEXIT_CRITICAL(&counter_lock);
        if (lost) event_log_append(EVENT_BOARD_OFFLINE, 0, 0);
        if (lost) ESP_LOGW(TAG, "Board contact offline; no automatic device start/stop or history restore");
        if (length > 0) {
            if (parser.used && now - last_rx >= CONFIG_MODULE_FRAME_GAP_MS)
                module_parser_reset_partial(&parser);
            last_rx = now;
            if (!pending_command && now < guard_until)
                guard_until = now + CONFIG_MODULE_QUERY_GUARD_MS;
            module_parser_feed(&parser, bytes, (size_t)length, receive_frame, NULL);
        } else if (parser.used && now - last_rx >= CONFIG_MODULE_FRAME_GAP_MS) {
            module_parser_reset_partial(&parser);
        }
        portENTER_CRITICAL(&counter_lock);
        counters.bad_lengths = parser.bad_lengths;
        counters.bad_checksums = parser.bad_checksums;
        counters.partial_timeouts = parser.partial_timeouts;
        counters.partial_discards = parser.partial_discards;
        portEXIT_CRITICAL(&counter_lock);
        if (pending_command && now >= reply_deadline) {
            count(&counters.reply_timeouts);
            portENTER_CRITICAL(&counter_lock); module_peer_timeout(&peer); portEXIT_CRITICAL(&counter_lock);
            ESP_LOGD(TAG, "Reply %02X timed out; no automatic write retry", pending_command);
            pending_command = 0;
            module_parser_reset_partial(&parser);
            guard_until = now + CONFIG_MODULE_QUERY_GUARD_MS;
        }
        if (pending_command || now < guard_until || parser.used) continue;
        bool queued = xQueueReceive(requests, &outgoing, 0) == pdTRUE;
        if (!queued && now >= next_poll) {
            uint8_t query = 1;
            outgoing.size = module_encode(0xb2, &query, 1, outgoing.frame, sizeof(outgoing.frame));
            queued = true;
            next_poll = now + CONFIG_MODULE_STATUS_POLL_MS;
        }
        if (queued && transmit(outgoing.frame, outgoing.size)) {
            pending_command = outgoing.frame[4];
            pending_event_revision = board_event_revision;
            pending_params_revision = params_event_revision;
            /* Variable B1/B3 replies can also occupy 4.27s at 9600 8N1. */
            reply_deadline = now + (int64_t)module_reply_budget_ms(pending_command, outgoing.size, CONFIG_MODULE_REPLY_TIMEOUT_MS);
        }
    }
}
esp_err_t field_bus_init(void)
{
    module_parser_init(&parser);
    uart_config_t config = {
        .baud_rate = 9600, .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t error = uart_param_config(PORT, &config);
    if (error != ESP_OK) return error;
    error = uart_set_pin(PORT, BOARD_FIELD_TX, BOARD_FIELD_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (error != ESP_OK) return error;
    error = uart_driver_install(PORT, 8192, 4096, UART_QUEUE_CAPACITY, &uart_events, 0);
    if (error != ESP_OK) return error;
    requests = xQueueCreate(4, sizeof(request_t));
    if (!requests) return ESP_ERR_NO_MEM;
    next_poll = 500;
    portENTER_CRITICAL(&counter_lock);
    module_peer_start(&peer, (uint64_t)(esp_timer_get_time() / 1000));
    portEXIT_CRITICAL(&counter_lock);
    ESP_LOGI(TAG, "TTL UART0 TX=%d RX=%d 9600 8N1; DE stays low", BOARD_FIELD_TX, BOARD_FIELD_RX);
    supervision_expect(MODULE_WATCH_FIELD);
    if (xTaskCreate(field_task, "field_uart", 6144, NULL, 6, NULL) == pdPASS) return ESP_OK;
    supervision_disable(MODULE_WATCH_FIELD);
    return ESP_ERR_NO_MEM;
}
