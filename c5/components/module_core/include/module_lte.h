#ifndef MODULE_LTE_H
#define MODULE_LTE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define MODULE_LTE_CHUNK 256
typedef enum { LTE_NONE, LTE_SIGNAL, LTE_REGISTER, LTE_ATTACH, LTE_PDP,
               LTE_ADDRESS, LTE_OPEN, LTE_SEND, LTE_READ, LTE_CLOSE,
               LTE_STATE, LTE_DISCONNECT, LTE_RECEIVE, LTE_CONTEXT } module_lte_kind_t;
typedef struct {
    module_lte_kind_t kind;
    unsigned id, value, extra;
    uint8_t data[MODULE_LTE_CHUNK];
    size_t size;
    bool payload_present;
    char address[16];
    char apn[101];
} module_lte_event_t;
bool module_lte_parse(const char *line, module_lte_event_t *event);
bool module_lte_host_valid(const char *host);
bool module_lte_apn_valid(const char *apn);
size_t module_lte_hex(const uint8_t *data, size_t size, char *out, size_t capacity);
#endif
