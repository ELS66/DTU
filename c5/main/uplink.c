#include "uplink.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include "network.h"
#include "modem.h"
#include "module_lte.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
static SemaphoreHandle_t mutex;
static portMUX_TYPE guard = portMUX_INITIALIZER_UNLOCKED;
static uplink_status_t status, live;
static module_route_policy_t policy;
static int wifi_socket = -1;
static uint32_t modem_session;
static uint64_t now_ms(void) { return (uint64_t)(esp_timer_get_time() / 1000); }
static void publish(void)
{
    live.last_success = policy.last_success;
    live.wifi_retry_after_ms = policy.wifi_retry_after_ms;
    portENTER_CRITICAL(&guard); status = live; portEXIT_CRITICAL(&guard);
}
void uplink_get_status(uplink_status_t *out)
{
    portENTER_CRITICAL(&guard); *out = status; portEXIT_CRITICAL(&guard);
}
static bool take(void) { return mutex && xSemaphoreTake(mutex, pdMS_TO_TICKS(1000)) == pdPASS; }
static esp_err_t wifi_open(const char *host, uint16_t port)
{
    char service[6];
    snprintf(service, sizeof(service), "%u", port);
    struct addrinfo hints = {.ai_family = AF_INET, .ai_socktype = SOCK_STREAM}, *addresses = NULL;
    if (getaddrinfo(host, service, &hints, &addresses) || !addresses) return ESP_FAIL;
    esp_err_t result = ESP_FAIL;
    /* Bound connect attempts; DNS itself uses the SDK resolver retry limits. */
    uint64_t deadline = now_ms() + 5000;
    for (struct addrinfo *address = addresses; address && now_ms() < deadline; address = address->ai_next) {
        int fd = socket(address->ai_family, address->ai_socktype, address->ai_protocol);
        if (fd < 0) continue;
        int flags = fcntl(fd, F_GETFL, 0);
        if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) { close(fd); continue; }
        int connected = connect(fd, address->ai_addr, address->ai_addrlen);
        if (connected && errno == EINPROGRESS) {
            fd_set writes; FD_ZERO(&writes); FD_SET(fd, &writes);
            uint64_t current = now_ms();
            uint64_t remaining = deadline > current ? deadline - current : 0;
            struct timeval timeout = {.tv_sec = remaining / 1000, .tv_usec = (remaining % 1000) * 1000};
            if (select(fd + 1, NULL, &writes, NULL, &timeout) > 0) {
                int error = 0; socklen_t length = sizeof(error);
                connected = getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &length) == 0 && !error ? 0 : -1;
            }
        }
        if (!connected && fcntl(fd, F_SETFL, flags) == 0) {
            struct timeval timeout = {.tv_sec = 5};
            if (setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) == 0) {
                wifi_socket = fd; result = ESP_OK; break;
            }
        }
        close(fd);
    }
    freeaddrinfo(addresses);
    return result;
}
static esp_err_t open_route(module_link_t route, const char *host, uint16_t port)
{
    esp_err_t error = route == MODULE_LINK_WIFI ? wifi_open(host, port) : modem_tcp_open(host, port, &modem_session);
    module_route_result(&policy, route, error == ESP_OK, now_ms());
    if (error != ESP_OK) {
        if (route == MODULE_LINK_WIFI) ++live.wifi_failures;
        else ++live.lte_failures;
    }
    return error;
}
esp_err_t uplink_open(uplink_mode_t mode, const char *host, uint16_t port, uint32_t *token)
{
    if (!token || !port || !module_lte_host_valid(host) || mode < UPLINK_AUTO || mode > UPLINK_LTE) return ESP_ERR_INVALID_ARG;
    *token = 0;
    if (!take()) return ESP_ERR_TIMEOUT;
    esp_err_t error = ESP_ERR_INVALID_STATE;
    if (live.active || live.token == UINT32_MAX) goto done;
    network_status_t wifi;
    modem_status_t lte;
    network_get_status(&wifi); modem_get_status(&lte);
    bool lte_ready = lte.data_ready && now_ms() - lte.data_observed_ms < 20000;
    module_link_t route = mode == UPLINK_WIFI ? MODULE_LINK_WIFI : mode == UPLINK_LTE ? MODULE_LINK_LTE :
                         module_route_choose(&policy, now_ms(), wifi.wifi_ip, lte_ready);
    if (route == MODULE_LINK_NONE || (route == MODULE_LINK_WIFI && !wifi.wifi_ip) ||
        (route == MODULE_LINK_LTE && !lte_ready)) goto done;
    error = open_route(route, host, port);
    if (error != ESP_OK && mode == UPLINK_AUTO && route == MODULE_LINK_WIFI && lte_ready) {
        route = MODULE_LINK_LTE;
        error = open_route(route, host, port);
    }
    if (error == ESP_OK) {
        live.active = true; live.route = route; ++live.token;
        *token = live.token;
    }
done:
    live.last_error = error; publish(); xSemaphoreGive(mutex); return error;
}
static esp_err_t close_current(void)
{
    esp_err_t error = ESP_OK;
    if (live.route == MODULE_LINK_WIFI && wifi_socket >= 0) { close(wifi_socket); wifi_socket = -1; }
    else if (live.route == MODULE_LINK_LTE) error = modem_tcp_close(modem_session);
    live.active = false; live.route = MODULE_LINK_NONE;
    return error;
}
esp_err_t uplink_write(uint32_t token, const uint8_t *bytes, size_t size)
{
    if (!bytes || !size || size > 4096) return ESP_ERR_INVALID_ARG;
    if (!take()) return ESP_ERR_TIMEOUT;
    esp_err_t error = ESP_ERR_INVALID_STATE;
    if (!live.active || live.token != token) goto done;
    size_t sent = 0;
    while (sent < size) {
        if (live.route == MODULE_LINK_WIFI) {
            int n = send(wifi_socket, bytes + sent, size - sent, 0);
            if (n <= 0) { error = ESP_FAIL; break; }
            sent += (size_t)n;
        } else {
            size_t chunk = size - sent > MODULE_LTE_CHUNK ? MODULE_LTE_CHUNK : size - sent;
            error = modem_tcp_write(modem_session, bytes + sent, chunk);
            if (error != ESP_OK) break;
            sent += chunk;
        }
    }
    if (sent == size) error = ESP_OK;
    if (error != ESP_OK) {
        ++live.uncertain_writes;
        module_route_result(&policy, live.route, false, now_ms());
        close_current(); /* No fallback or replay after any application write. */
    }
done:
    live.last_error = error; publish(); xSemaphoreGive(mutex); return error;
}
esp_err_t uplink_read(uint32_t token, uint8_t *bytes, size_t capacity, size_t *received, unsigned timeout_ms)
{
    if (!bytes || !capacity || !received || !timeout_ms || timeout_ms > 30000) return ESP_ERR_INVALID_ARG;
    *received = 0;
    if (!take()) return ESP_ERR_TIMEOUT;
    esp_err_t error = ESP_ERR_INVALID_STATE;
    if (!live.active || live.token != token) goto done;
    if (live.route == MODULE_LINK_WIFI) {
        struct timeval timeout = {.tv_sec = timeout_ms / 1000, .tv_usec = (timeout_ms % 1000) * 1000};
        if (setsockopt(wifi_socket, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout))) error = ESP_FAIL;
        else {
            int n = recv(wifi_socket, bytes, capacity, 0);
            if (n > 0) { *received = n; error = ESP_OK; }
            else error = n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK) ? ESP_ERR_TIMEOUT : ESP_FAIL;
        }
    } else {
        uint64_t deadline = now_ms() + timeout_ms;
        do {
            error = modem_tcp_read(modem_session, bytes, capacity > MODULE_LTE_CHUNK ? MODULE_LTE_CHUNK : capacity, received);
            if (error != ESP_OK || *received) break;
            if (now_ms() >= deadline) { error = ESP_ERR_TIMEOUT; break; }
            vTaskDelay(pdMS_TO_TICKS(100));
        } while (true);
    }
    if (error != ESP_OK && error != ESP_ERR_TIMEOUT) {
        module_route_result(&policy, live.route, false, now_ms());
        close_current();
    }
done:
    live.last_error = error; publish(); xSemaphoreGive(mutex); return error;
}
esp_err_t uplink_close(uint32_t token)
{
    if (!take()) return ESP_ERR_TIMEOUT;
    esp_err_t error = ESP_ERR_INVALID_STATE;
    if (live.active && live.token == token) error = close_current();
    live.last_error = error; publish(); xSemaphoreGive(mutex); return error;
}
esp_err_t uplink_init(void)
{
    mutex = xSemaphoreCreateMutex();
    if (!mutex) return ESP_ERR_NO_MEM;
    live.initialized = true; publish(); return ESP_OK;
}
