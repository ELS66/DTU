#include "module_events.h"
#include <string.h>
void module_events_init(module_events_t *e) { if (e) memset(e, 0, sizeof(*e)); }
bool module_events_append(module_events_t *e, uint32_t code, uint32_t detail, uint32_t value, uint64_t now)
{
    if (!e) return false;
    if (!code || e->last_sequence == UINT64_MAX) {
        if (e->rejected != UINT32_MAX) ++e->rejected;
        return false;
    }
    if (now < e->last_ms) now = e->last_ms;
    size_t index = (e->head + e->count) % MODULE_EVENTS_CAPACITY;
    if (e->count == MODULE_EVENTS_CAPACITY) {
        index = e->head;
        e->head = (e->head + 1) % MODULE_EVENTS_CAPACITY;
        if (e->overwritten != UINT64_MAX) ++e->overwritten;
    } else ++e->count;
    e->entries[index] = (module_event_t){.sequence = ++e->last_sequence, .uptime_ms = now,
                                      .code = code, .detail = detail, .value = value};
    e->last_ms = now;
    return true;
}
bool module_events_page(const module_events_t *e, uint64_t after, size_t limit, module_events_page_t *out)
{
    if (!e || !out || !limit || limit > MODULE_EVENTS_PAGE_MAX) return false;
    memset(out, 0, sizeof(*out));
    out->retained = e->count; out->latest = e->last_sequence;
    out->oldest = e->count ? e->entries[e->head].sequence : 0;
    out->overwritten = e->overwritten; out->rejected = e->rejected; out->next_cursor = after;
    out->gap = out->oldest && after < out->oldest - 1;
    out->cursor_ahead = after > out->latest;
    for (size_t i = 0; i < e->count && out->count < limit; ++i) {
        const module_event_t *entry = &e->entries[(e->head + i) % MODULE_EVENTS_CAPACITY];
        if (entry->sequence > after) out->entries[out->count++] = *entry;
    }
    if (out->count) out->next_cursor = out->entries[out->count-1].sequence;
    return true;
}
