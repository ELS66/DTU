#include "module_supervision.h"
static void increment(uint32_t *value) { if (*value != UINT32_MAX) ++*value; }
bool module_watch_enable(module_watch_t *w, unsigned id, uint32_t budget, uint64_t now)
{
    if (!w || id >= MODULE_WATCH_COUNT || !budget || w->slots[id].enabled || w->fault_mask) return false;
    w->slots[id] = (module_watch_slot_t){.enabled = true, .budget_ms = budget, .last_progress_ms = now};
    return true;
}
void module_watch_disable(module_watch_t *w, unsigned id)
{
    if (w && id < MODULE_WATCH_COUNT) w->slots[id].enabled = false;
}
bool module_watch_progress(module_watch_t *w, unsigned id, uint64_t now)
{
    if (!w || id >= MODULE_WATCH_COUNT || !w->slots[id].enabled || now < w->slots[id].last_progress_ms) return false;
    w->slots[id].last_progress_ms = now;
    increment(&w->slots[id].advances);
    return true;
}
uint32_t module_watch_evaluate(module_watch_t *w, uint64_t now)
{
    if (!w || w->fault_mask) return w ? w->fault_mask : 0;
    for (unsigned i = 0; i < MODULE_WATCH_COUNT; ++i) {
        const module_watch_slot_t *s = &w->slots[i];
        if (s->enabled && (now < s->last_progress_ms || now - s->last_progress_ms >= s->budget_ms))
            w->fault_mask |= 1u << i;
    }
    if (w->fault_mask) w->fault_ms = now;
    return w->fault_mask;
}
bool module_uart_pressure(module_uart_health_t *h, unsigned queued, unsigned capacity)
{
    if (!h || !capacity) return false;
    if (queued > h->queue_peak) h->queue_peak = queued;
    if ((uint64_t)queued * 4 >= (uint64_t)capacity * 3) increment(&h->pressure_batches);
    return queued >= capacity;
}
void module_uart_fault(module_uart_health_t *h, uint32_t flags, uint64_t now, uint32_t guard)
{
    if (!h || !flags) return;
    increment(&h->fault_batches); increment(&h->consecutive_faults);
    if (flags & MODULE_UART_FIFO) increment(&h->fifo);
    if (flags & MODULE_UART_BUFFER) increment(&h->buffer);
    if (flags & MODULE_UART_FRAME) increment(&h->frame);
    if (flags & MODULE_UART_PARITY) increment(&h->parity);
    if (flags & MODULE_UART_BREAK) increment(&h->breaks);
    if (flags & MODULE_UART_QUEUE_FULL) increment(&h->queue_full);
    if (flags & MODULE_UART_READ) increment(&h->read_errors);
    h->recovering = true; h->last_flags = flags; h->last_fault_ms = now;
    h->guard_until_ms = UINT64_MAX - now < guard ? UINT64_MAX : now + guard;
}
bool module_uart_good(module_uart_health_t *h, uint64_t now)
{
    if (!h || !h->recovering || now < h->guard_until_ms) return false;
    h->recovering = false; h->consecutive_faults = 0; increment(&h->recoveries);
    return true;
}
