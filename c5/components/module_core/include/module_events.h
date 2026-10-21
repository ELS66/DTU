#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define MODULE_EVENTS_CAPACITY 64u
#define MODULE_EVENTS_PAGE_MAX 16u
typedef struct {
    uint64_t sequence, uptime_ms;
    uint32_t code, detail, value;
} module_event_t;
typedef struct {
    module_event_t entries[MODULE_EVENTS_CAPACITY];
    size_t head, count;
    uint64_t last_sequence, overwritten, last_ms;
    uint32_t rejected;
} module_events_t;
typedef struct {
    module_event_t entries[MODULE_EVENTS_PAGE_MAX];
    size_t count, retained;
    uint64_t oldest, latest, next_cursor, overwritten;
    uint32_t rejected;
    bool gap, cursor_ahead;
} module_events_page_t;
void module_events_init(module_events_t *events);
/* Caller serializes access. Timestamps clamp to the last append across task scheduling. */
bool module_events_append(module_events_t *events, uint32_t code, uint32_t detail, uint32_t value, uint64_t now);
/* Returns retained entries strictly after the cursor, in increasing sequence order. */
bool module_events_page(const module_events_t *events, uint64_t after, size_t limit, module_events_page_t *out);
