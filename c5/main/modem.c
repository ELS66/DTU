#include "modem.h"
#include "supervision.h"
#include "event_log.h"
#include <stdio.h>
#include <string.h>
#include "board.h"
#include "module_at.h"
#include "module_lte.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "sdkconfig.h"
#define MODEM_UART UART_NUM_1
typedef enum { REQUEST_OPEN, REQUEST_SEND, REQUEST_READ, REQUEST_CLOSE } request_kind_t;
typedef struct {
    request_kind_t kind;
    char host[128];
    uint16_t port;
    uint32_t session;
    size_t size, received;
    uint8_t bytes[MODULE_LTE_CHUNK];
    esp_err_t error;
} request_t;
typedef struct {
    module_lte_kind_t expected;
    bool seen, conflict, identity;
    module_lte_event_t event;
    char text[64];
} capture_t;
typedef struct { module_at_t at; capture_t capture; } reply_t;
static const char *TAG = "modem";
static portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
static modem_status_t status, live;
static QueueHandle_t uart_events, requests;
static SemaphoreHandle_t rpc_lock, completed;
static request_t rpc;
static module_at_t stream;
static capture_t idle_capture;
static bool configured, socket_dirty, remote_closed;
static int64_t next_activation, quarantine_until;
static int64_t now_ms(void) { return esp_timer_get_time() / 1000; }
static void publish(void)
{
    portENTER_CRITICAL(&lock);
    modem_status_t previous = status;
    status = live;
    portEXIT_CRITICAL(&lock);
    if (previous.sim != live.sim) event_log_append(EVENT_MODEM_SIM, live.sim, previous.sim);
    if (previous.at_ready != live.at_ready) event_log_append(EVENT_MODEM_AT, live.at_ready, 0);
    if (previous.registration != live.registration) event_log_append(EVENT_MODEM_REGISTRATION, live.registration, previous.registration);
    if (previous.data_ready != live.data_ready) event_log_append(EVENT_MODEM_DATA, live.data_ready, 0);
}
void modem_get_status(modem_status_t *out)
{
    portENTER_CRITICAL(&lock); *out = status; portEXIT_CRITICAL(&lock);
}
static void line_received(void *context, const char *line)
{
    capture_t *capture = context;
    module_lte_event_t event;
    if (module_lte_parse(line, &event)) {
        if (event.id == 0 && event.kind == LTE_DISCONNECT) {
            live.socket_connected = false;
            remote_closed = true; /* Drain buffered tail bytes before reporting EOF. */
        } else if (event.id == 0 && event.kind == LTE_CLOSE) {
            live.socket_connected = false;
            socket_dirty = true;
        }
        bool expected_id = event.kind == LTE_PDP || event.kind == LTE_ADDRESS || event.kind == LTE_CONTEXT ? event.id == 1 : event.id == 0;
        if (event.kind == capture->expected && expected_id) {
            if (capture->seen) capture->conflict = true;
            capture->seen = true;
            capture->event = event;
        }
    }
    if (capture->identity && !capture->text[0] && *line &&
        strcmp(line, "OK") && strcmp(line, "ERROR") && strncmp(line, "AT", 2) &&
        strncmp(line, "+CME", 4) && strncmp(line, "+MIP", 4) && strncmp(line, "+CPIN", 5))
        snprintf(capture->text, sizeof(capture->text), "%.63s", line);
}
static void collect_uart_errors(module_at_t *parser)
{
    uart_event_t event;
    while (xQueueReceive(uart_events, &event, 0)) {
        if (event.type == UART_FIFO_OVF || event.type == UART_BUFFER_FULL ||
            event.type == UART_FRAME_ERR || event.type == UART_PARITY_ERR) {
            parser->damaged = true;
            ++live.uart_errors;
            live.socket_connected = false; socket_dirty = true;
        }
    }
}
static void pump(module_at_t *parser, unsigned wait_ms)
{
    uint8_t bytes[256];
    int n = uart_read_bytes(MODEM_UART, bytes, sizeof(bytes), pdMS_TO_TICKS(wait_ms));
    collect_uart_errors(parser);
    if (n > 0) module_at_feed(parser, bytes, (size_t)n);
}
static void drain(unsigned milliseconds)
{
    stream.on_line = line_received; stream.context = &idle_capture;
    int64_t until = now_ms() + milliseconds;
    do { pump(&stream, 20); } while (now_ms() < until);
    module_at_init(&stream, MODULE_AT_BASIC);
    stream.on_line = line_received; stream.context = &idle_capture;
}
static reply_t transaction(const char *command, module_at_kind_t kind,
                           module_lte_kind_t expected, unsigned timeout, bool identity)
{
    reply_t reply = {0};
    stream.kind = kind; stream.result = MODULE_AT_PENDING; stream.damaged = false;
    stream.saw_sim = false; stream.sim = stream.candidate = MODULE_SIM_UNKNOWN; stream.cme_error = -1;
    reply.capture.expected = expected; reply.capture.identity = identity;
    stream.on_line = line_received; stream.context = &reply.capture;
    /* One UART owner, passive HEX receive. Dispatch URCs even after a command's OK. */
    if (uart_write_bytes(MODEM_UART, command, strlen(command)) != (int)strlen(command) ||
        uart_wait_tx_done(MODEM_UART, pdMS_TO_TICKS(500)) != ESP_OK) stream.damaged = true;
    int64_t until = now_ms() + timeout;
    for (;;) {
        pump(&stream, 20);
        if (stream.result == MODULE_AT_ERROR || stream.damaged || reply.capture.conflict) break;
        if (stream.result == MODULE_AT_OK &&
            (expected == LTE_NONE || reply.capture.seen || expected == LTE_READ)) break;
        if (now_ms() >= until) break;
    }
    collect_uart_errors(&stream);
    reply.at = stream;
    bool incomplete = reply.at.result == MODULE_AT_PENDING ||
                      (reply.at.result == MODULE_AT_OK && expected != LTE_NONE && expected != LTE_READ && !reply.capture.seen);
    if (reply.at.damaged || reply.capture.conflict || incomplete) {
        reply.at.sim = MODULE_SIM_UNKNOWN;
        reply.at.result = MODULE_AT_ERROR;
        if (incomplete) { ++live.timeouts; quarantine_until = now_ms() + 2000; }
        drain(500);
    }
    reply.at.on_line = NULL; reply.at.context = NULL;
    stream.on_line = line_received; stream.context = &idle_capture;
    /* A transaction progressed only after its bounded result/timeout and drain. */
    supervision_progress(MODULE_WATCH_MODEM);
    return reply;
}
static bool success(const reply_t *reply)
{
    return reply->at.result == MODULE_AT_OK && !reply->at.damaged && !reply->capture.conflict;
}
static bool basic(const char *command, unsigned timeout)
{
    reply_t reply = transaction(command, MODULE_AT_BASIC, LTE_NONE, timeout, false);
    live.last_cme = reply.at.cme_error;
    return success(&reply);
}
static bool query(const char *command, module_lte_kind_t kind, module_lte_event_t *event)
{
    reply_t reply = transaction(command, MODULE_AT_BASIC, kind, 2000, false);
    live.last_cme = reply.at.cme_error;
    if (!success(&reply) || !reply.capture.seen) return false;
    *event = reply.capture.event;
    return true;
}
static void identify(void)
{
    reply_t model = transaction("AT+CGMM\r\n", MODULE_AT_BASIC, LTE_NONE, 1500, true);
    if (success(&model)) snprintf(live.model, sizeof(live.model), "%s", model.capture.text);
    reply_t revision = transaction("AT+CGMR\r\n", MODULE_AT_BASIC, LTE_NONE, 1500, true);
    if (success(&revision)) snprintf(live.revision, sizeof(live.revision), "%s", revision.capture.text);
    live.model_matches = strstr(live.model, "ML307R") != NULL;
    ESP_LOGI(TAG, "Model=%s revision=%s expected_ML307R=%d", live.model, live.revision, live.model_matches);
}
static void monitor(module_sim_filter_t *filter)
{
    if (!live.at_ready) live.at_ready = basic("AT\r\n", 750);
    if (live.at_ready && !configured) {
        basic("ATE0\r\n", 1000);
        basic("AT+CMEE=2\r\n", 1000);
        identify();
        configured = true;
    }
    module_sim_t sim = MODULE_SIM_UNKNOWN;
    if (live.at_ready) {
        reply_t reply = transaction("AT+CPIN?\r\n", MODULE_AT_SIM, LTE_NONE, 2000, false);
        sim = reply.at.sim; live.last_cme = reply.at.cme_error;
        /* An explicit CME response also proves the AT channel answered. */
        live.at_ready = !reply.at.damaged && (success(&reply) || reply.at.cme_error >= 0 ||
                        reply.at.sim == MODULE_SIM_ABSENT || reply.at.result == MODULE_AT_ERROR);
        if (reply.at.result == MODULE_AT_ERROR && reply.at.cme_error < 0 &&
            reply.at.sim == MODULE_SIM_UNKNOWN) live.at_ready = basic("AT\r\n", 750);
        if (!live.at_ready) configured = false;
    }
    live.sim = module_sim_confirm(filter, sim);
    live.observed_ms = now_ms();
    publish(); /* Keep SIM observations independent from a potentially slow activation. */
    if (live.sim != MODULE_SIM_PRESENT || !live.model_matches) {
        live.registration = live.rssi = 99;
        live.attached = live.pdp_active = live.data_ready = false;
        live.pdp_ipv4[0] = 0;
        live.socket_connected = false; socket_dirty = true;
        return;
    }
    live.registration = 99; live.rssi = 99;
    live.attached = live.pdp_active = live.data_ready = false;
    live.pdp_ipv4[0] = 0;
    module_lte_event_t event;
    if (query("AT+CSQ\r\n", LTE_SIGNAL, &event)) live.rssi = event.value;
    if (query("AT+CEREG?\r\n", LTE_REGISTER, &event)) live.registration = event.value;
    if (live.registration != 1 && live.registration != 5) {
        live.socket_connected = false; socket_dirty = true;
        return;
    }
    if (query("AT+CGATT?\r\n", LTE_ATTACH, &event)) live.attached = event.value == 1;
    if (query("AT+CGACT?\r\n", LTE_PDP, &event)) live.pdp_active = event.value == 1;
    live.apn_matches = !CONFIG_MODULE_MODEM_APN[0];
    if (CONFIG_MODULE_MODEM_APN[0] && query("AT+CGDCONT?\r\n", LTE_CONTEXT, &event))
        live.apn_matches = !strcmp(event.apn, CONFIG_MODULE_MODEM_APN);
    if ((!live.attached || !live.pdp_active) && now_ms() >= next_activation) {
        next_activation = now_ms() + 30000;
        if (!live.attached) live.attached = basic("AT+CGATT=1\r\n", 30000);
        if (live.attached && !live.pdp_active) {
            if (!live.apn_matches && CONFIG_MODULE_MODEM_APN[0]) {
                char command[160];
                snprintf(command, sizeof(command), "AT+CGDCONT=1,\"IPV4V6\",\"%s\"\r\n", CONFIG_MODULE_MODEM_APN);
                live.apn_matches = basic(command, 2000);
            }
            if (live.apn_matches) basic("AT+CGACT=1,1\r\n", 30000);
            if (query("AT+CGACT?\r\n", LTE_PDP, &event)) live.pdp_active = event.value == 1;
        }
        next_activation = now_ms() + 30000;
    }
    if (live.apn_matches && live.attached && live.pdp_active && query("AT+CGPADDR=1\r\n", LTE_ADDRESS, &event)) {
        snprintf(live.pdp_ipv4, sizeof(live.pdp_ipv4), "%s", event.address);
        live.data_ready = true;
    }
    if (!live.data_ready) { live.socket_connected = false; socket_dirty = true; }
    live.data_observed_ms = now_ms();
}
static esp_err_t ensure_closed(void)
{
    live.socket_connected = false;
    /* ML307R does not support MIPCLOSE's mode argument. Verify the final state. */
    basic("AT+MIPCLOSE=0\r\n", 5000);
    module_lte_event_t event;
    if (!query("AT+MIPSTATE=0\r\n", LTE_STATE, &event) || event.value != 0) {
        socket_dirty = true;
        return ESP_ERR_INVALID_STATE;
    }
    socket_dirty = false;
    remote_closed = false;
    return ESP_OK;
}
static void perform_request(void)
{
    rpc.error = ESP_ERR_INVALID_STATE; rpc.received = 0;
    if (rpc.kind == REQUEST_CLOSE) {
        if (rpc.session == live.socket_session) rpc.error = ensure_closed();
        return;
    }
    if (!live.data_ready || now_ms() - live.data_observed_ms > 20000 ||
        !live.model_matches || now_ms() < quarantine_until) return;
    if (rpc.kind == REQUEST_OPEN) {
        if (live.socket_connected) return;
        rpc.error = ensure_closed();
        if (rpc.error != ESP_OK) return;
        if (live.socket_session == UINT32_MAX) { rpc.error = ESP_ERR_INVALID_STATE; return; }
        ++live.socket_session;
        rpc.session = live.socket_session;
        if (!basic("AT+MIPCFG=\"cid\",0,1\r\n", 2000) ||
            !basic("AT+MIPCFG=\"encoding\",0,1,1\r\n", 2000) ||
            !basic("AT+MIPCFG=\"autofree\",0,1\r\n", 2000) ||
            !basic("AT+MIPCFG=\"ssl\",0,0\r\n", 2000)) { rpc.error = ESP_FAIL; return; }
        char command[200];
        snprintf(command, sizeof(command), "AT+MIPOPEN=0,\"TCP\",\"%s\",%u,15,2\r\n", rpc.host, rpc.port);
        reply_t reply = transaction(command, MODULE_AT_BASIC, LTE_OPEN, 22000, false);
        if (!success(&reply) || reply.capture.event.value != 0) {
            rpc.error = ESP_FAIL; socket_dirty = true;
            quarantine_until = now_ms() + 15000;
            return;
        }
        if (remote_closed) { socket_dirty = true; rpc.error = ESP_FAIL; return; }
        live.socket_connected = true; socket_dirty = false; rpc.error = ESP_OK;
        return;
    }
    if (rpc.session != live.socket_session || socket_dirty ||
        (!live.socket_connected && !(rpc.kind == REQUEST_READ && remote_closed))) return;
    if (rpc.kind == REQUEST_SEND) {
        char hex[MODULE_LTE_CHUNK*2+1], command[MODULE_LTE_CHUNK*2+64];
        module_lte_hex(rpc.bytes, rpc.size, hex, sizeof(hex));
        snprintf(command, sizeof(command), "AT+MIPSEND=0,%u,\"%s\"\r\n", (unsigned)rpc.size, hex);
        reply_t reply = transaction(command, MODULE_AT_BASIC, LTE_SEND, 5000, false);
        if (success(&reply) && reply.capture.event.value == rpc.size && live.socket_connected) rpc.error = ESP_OK;
        else {
            ++live.uncertain_sends;
            live.socket_connected = false; socket_dirty = true;
            rpc.error = ESP_FAIL; /* Never retry an ambiguous application write. */
        }
    } else if (rpc.kind == REQUEST_READ) {
        char command[48];
        snprintf(command, sizeof(command), "AT+MIPRD=0,%u\r\n", (unsigned)rpc.size);
        reply_t reply = transaction(command, MODULE_AT_BASIC, LTE_READ, 2500, false);
        if (success(&reply) && reply.capture.event.size <= rpc.size &&
            (!reply.capture.seen || reply.capture.event.payload_present)) {
            rpc.received = reply.capture.seen ? reply.capture.event.size : 0;
            memcpy(rpc.bytes, reply.capture.event.data, rpc.received);
            rpc.error = ESP_OK;
            if (!rpc.received && remote_closed) rpc.error = ESP_ERR_NOT_FOUND;
        } else {
            live.socket_connected = false; socket_dirty = true; rpc.error = ESP_FAIL;
        }
    }
}
static void modem_task(void *unused)
{
    (void)unused;
    live.started = true; live.last_cme = -1; live.rssi = live.registration = 99;
    module_at_init(&stream, MODULE_AT_BASIC);
    stream.on_line = line_received; stream.context = &idle_capture;
    publish();
    vTaskDelay(pdMS_TO_TICKS(750));
    for (unsigned i = 0; i < 3 && !live.at_ready; ++i) live.at_ready = basic("AT\r\n", 750);
    if (!live.at_ready) {
        ESP_LOGW(TAG, "No AT response; one 2500ms PWRKEY pulse. No automatic RESET.");
        gpio_set_level(BOARD_LTE_PWRKEY, 1);
        vTaskDelay(pdMS_TO_TICKS(2500));
        gpio_set_level(BOARD_LTE_PWRKEY, 0);
        live.power_pulsed = true;
        for (unsigned i = 0; i < 15 && !live.at_ready; ++i) {
            vTaskDelay(pdMS_TO_TICKS(500));
            live.at_ready = basic("AT\r\n", 750);
        }
    }
    module_sim_filter_t filter = {0};
    int64_t next_monitor = 0;
    for (;;) {
        if (now_ms() >= next_monitor) {
            module_sim_t before = live.sim;
            monitor(&filter);
            if (before != live.sim) ESP_LOGI(TAG, "SIM=%d registration=%u PDP=%d (0 unknown,1 absent,2 ready,3 locked)",
                                             live.sim, live.registration, live.pdp_active);
            next_monitor = now_ms() + 5000;
            publish();
        }
        request_kind_t request;
        if (xQueueReceive(requests, &request, 0) == pdPASS) {
            (void)request;
            perform_request();
            publish();
            xSemaphoreGive(completed);
        }
        pump(&stream, 20);
        if (stream.damaged) {
            live.socket_connected = false; socket_dirty = true;
            module_at_init(&stream, MODULE_AT_BASIC);
            stream.on_line = line_received; stream.context = &idle_capture;
        }
        publish();
        supervision_progress(MODULE_WATCH_MODEM);
    }
}
static esp_err_t call(request_kind_t kind, uint32_t *session, const char *host, uint16_t port,
                      const uint8_t *data, uint8_t *out, size_t size, size_t *received)
{
    modem_status_t snapshot;
    modem_get_status(&snapshot);
    if (!snapshot.started || !rpc_lock) return ESP_ERR_INVALID_STATE;
    if (size > MODULE_LTE_CHUNK) return ESP_ERR_INVALID_SIZE;
    if (xSemaphoreTake(rpc_lock, pdMS_TO_TICKS(1000)) != pdPASS) return ESP_ERR_TIMEOUT;
    memset(&rpc, 0, sizeof(rpc));
    rpc.kind = kind; rpc.session = *session; rpc.port = port; rpc.size = size;
    if (host) snprintf(rpc.host, sizeof(rpc.host), "%s", host);
    if (data && size) memcpy(rpc.bytes, data, size);
    esp_err_t error = ESP_ERR_TIMEOUT;
    if (xQueueSend(requests, &kind, pdMS_TO_TICKS(1000)) == pdPASS) {
        /* Static request storage remains owned until the bounded worker operation finishes. */
        xSemaphoreTake(completed, portMAX_DELAY);
        error = rpc.error;
        *session = rpc.session;
        if (received) *received = rpc.received;
        if (out && rpc.received) memcpy(out, rpc.bytes, rpc.received);
    }
    memset(&rpc, 0, sizeof(rpc));
    xSemaphoreGive(rpc_lock);
    return error;
}
esp_err_t modem_tcp_open(const char *host, uint16_t port, uint32_t *session)
{
    if (!session || !port || !module_lte_host_valid(host)) return ESP_ERR_INVALID_ARG;
    *session = 0; return call(REQUEST_OPEN, session, host, port, NULL, NULL, 0, NULL);
}
esp_err_t modem_tcp_write(uint32_t session, const uint8_t *bytes, size_t size)
{
    if (!bytes || !size) return ESP_ERR_INVALID_ARG;
    return call(REQUEST_SEND, &session, NULL, 0, bytes, NULL, size, NULL);
}
esp_err_t modem_tcp_read(uint32_t session, uint8_t *bytes, size_t capacity, size_t *received)
{
    if (!bytes || !capacity || !received) return ESP_ERR_INVALID_ARG;
    *received = 0; return call(REQUEST_READ, &session, NULL, 0, NULL, bytes, capacity, received);
}
esp_err_t modem_tcp_close(uint32_t session)
{
    return call(REQUEST_CLOSE, &session, NULL, 0, NULL, NULL, 0, NULL);
}
esp_err_t modem_init(void)
{
    if (!module_lte_apn_valid(CONFIG_MODULE_MODEM_APN)) return ESP_ERR_INVALID_ARG;
    uart_config_t config = {.baud_rate = CONFIG_MODULE_MODEM_BAUD,
        .data_bits = UART_DATA_8_BITS, .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1, .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT};
    esp_err_t error = uart_param_config(MODEM_UART, &config);
    if (error != ESP_OK) return error;
    error = uart_set_pin(MODEM_UART, BOARD_LTE_TX, BOARD_LTE_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (error != ESP_OK) return error;
    error = uart_driver_install(MODEM_UART, 8192, 0, 32, &uart_events, 0);
    if (error != ESP_OK) return error;
    rpc_lock = xSemaphoreCreateMutex(); completed = xSemaphoreCreateBinary();
    requests = xQueueCreate(1, sizeof(request_kind_t));
    if (rpc_lock && completed && requests) {
        supervision_expect(MODULE_WATCH_MODEM);
        if (xTaskCreate(modem_task, "modem_at", 8192, NULL, 4, NULL) == pdPASS) return ESP_OK;
        supervision_disable(MODULE_WATCH_MODEM);
    }
    if (rpc_lock) { vSemaphoreDelete(rpc_lock); rpc_lock = NULL; }
    if (completed) { vSemaphoreDelete(completed); completed = NULL; }
    if (requests) { vQueueDelete(requests); requests = NULL; }
    uart_driver_delete(MODEM_UART);
    return ESP_ERR_NO_MEM;
}
