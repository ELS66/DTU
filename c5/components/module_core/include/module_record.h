#ifndef MODULE_RECORD_H
#define MODULE_RECORD_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define MODULE_RECORD_SIZE 36u
typedef struct {
    uint64_t sequence;
    uint32_t boot_tag;
    uint8_t state, source_command;
    uint16_t remaining_seconds;
    uint64_t observed_uptime_ms;
} module_record_t;
void module_record_encode(const module_record_t *record, uint8_t bytes[MODULE_RECORD_SIZE]);
bool module_record_decode(const uint8_t *bytes, size_t size, module_record_t *record);
#endif
