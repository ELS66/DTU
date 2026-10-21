#include "module_runtime_policy.h"
#include <string.h>
#include "module_protocol.h"
static void increment(uint32_t *value) { if (*value != UINT32_MAX) ++*value; }
static bool elapsed(uint64_t now, uint64_t start, uint64_t interval)
{
    return now >= start && now - start >= interval;
}
uint64_t module_state_timeout_ms(uint64_t configured, unsigned poll_ms, unsigned reply_ms)
{
    uint64_t minimum = (uint64_t)poll_ms * 3 + reply_ms;
    return configured > minimum ? configured : minimum;
}
uint64_t module_contact_timeout_ms(uint64_t state_timeout, unsigned poll_ms, unsigned reply_ms)
{
    uint64_t wire_ms = ((uint64_t)MODULE_FRAME_MAX * 10000 + 9599) / 9600;
    uint64_t minimum = (uint64_t)poll_ms * 3 + reply_ms + wire_ms;
    return state_timeout > minimum ? state_timeout : minimum;
}
module_state_freshness_t module_observation_freshness(const module_observation_t *live, uint64_t now, uint64_t stale_ms)
{
    if (!live->known) return MODULE_STATE_UNKNOWN;
    if (now < live->observed_uptime_ms || !stale_ms || elapsed(now, live->observed_uptime_ms, stale_ms))
        return MODULE_STATE_STALE;
    return MODULE_STATE_FRESH;
}
bool module_runtime_observe(module_runtime_policy_t *p, uint8_t command, uint8_t state,
                            uint16_t remaining, bool event, uint64_t now)
{
    if (!module_work_state_valid(state) || p->live.revision == UINT64_MAX ||
        (p->live.known && now < p->live.observed_uptime_ms)) return false;
    bool state_changed = !p->live.known || p->live.state != state;
    bool content_changed = state_changed || p->live.remaining_seconds != remaining;
    if (state_changed) p->event_known = false;
    bool duplicate = event && !content_changed && p->event_known && p->event_command == command &&
                     p->event_state == state && p->event_remaining == remaining;
    bool critical = state_changed || (event && !duplicate);
    if (!p->live.known) p->first_observed_ms = now;
    p->live.known = true; p->live.state = state; p->live.source_command = command;
    p->live.remaining_seconds = remaining; p->live.observed_uptime_ms = now; ++p->live.revision;
    if (event) {
        p->event_known = true; p->event_command = command; p->event_state = state;
        p->event_remaining = remaining;
        if (duplicate) increment(&p->duplicate_events);
    }
    if (critical) {
        bool already_pending = p->critical_pending;
        if (!already_pending || (p->saving && p->critical_revision <= p->captured_revision))
            p->critical_since_ms = now;
        if (already_pending) increment(&p->coalesced_changes);
        p->critical_pending = true; p->critical_revision = p->live.revision;
    }
    return true;
}
module_save_reason_t module_runtime_save_due(const module_runtime_policy_t *p, uint64_t now, uint64_t stale_ms)
{
    if (p->saving || module_observation_freshness(&p->live, now, stale_ms) != MODULE_STATE_FRESH ||
        p->live.revision == p->saved_revision || now < p->retry_after_ms) return MODULE_SAVE_NONE;
    if (!p->has_saved)
        return elapsed(now, p->first_observed_ms, MODULE_RECORD_DEBOUNCE_MS) ? MODULE_SAVE_FIRST : MODULE_SAVE_NONE;
    if (p->critical_pending && elapsed(now, p->critical_since_ms, MODULE_RECORD_DEBOUNCE_MS) &&
        elapsed(now, p->last_success_ms, MODULE_RECORD_MIN_GAP_MS)) return MODULE_SAVE_CRITICAL;
    if (elapsed(now, p->last_success_ms, MODULE_RECORD_INTERVAL_MS)) return MODULE_SAVE_PERIODIC;
    return MODULE_SAVE_NONE;
}
bool module_runtime_capture(module_runtime_policy_t *p, uint64_t now, uint64_t stale_ms,
                            module_observation_t *out, module_save_reason_t *reason)
{
    module_save_reason_t due = module_runtime_save_due(p, now, stale_ms);
    if (!out || !reason || due == MODULE_SAVE_NONE) return false;
    p->saving = true; p->captured_revision = p->live.revision;
    *out = p->live; *reason = due; return true;
}
bool module_runtime_save_finished(module_runtime_policy_t *p, uint64_t revision, bool success, uint64_t now)
{
    if (!p->saving || revision != p->captured_revision) return false;
    p->saving = false;
    if (!success) { p->retry_after_ms = now + MODULE_RECORD_RETRY_MS; return true; }
    p->saved_revision = revision; p->has_saved = true; p->last_success_ms = now; p->retry_after_ms = 0;
    if (p->critical_revision <= revision) p->critical_pending = false;
    return true;
}
void module_peer_start(module_peer_t *p, uint64_t now)
{
    memset(p, 0, sizeof(*p)); p->started = true; p->started_ms = now;
}
module_contact_state_t module_peer_state(const module_peer_t *p, uint64_t now, uint64_t timeout_ms)
{
    if (!p->started) return MODULE_CONTACT_NOT_STARTED;
    uint64_t anchor = p->ever_valid ? p->last_valid_ms : p->started_ms;
    if (!timeout_ms || now < anchor || elapsed(now, anchor, timeout_ms)) return MODULE_CONTACT_OFFLINE;
    return p->ever_valid ? MODULE_CONTACT_ONLINE : MODULE_CONTACT_WAITING;
}
void module_peer_tick(module_peer_t *p, uint64_t now, uint64_t timeout_ms)
{
    if (module_peer_state(p, now, timeout_ms) == MODULE_CONTACT_OFFLINE && !p->loss_latched) {
        p->loss_latched = true; increment(&p->loss_events);
    }
}
void module_peer_received(module_peer_t *p, uint64_t now, uint64_t timeout_ms, bool reply)
{
    if (!p->started) return;
    module_peer_tick(p, now, timeout_ms);
    if (p->loss_latched) increment(&p->recoveries);
    p->loss_latched = false; p->ever_valid = true; p->last_valid_ms = now;
    if (reply) p->consecutive_timeouts = 0;
}
void module_peer_timeout(module_peer_t *p) { increment(&p->consecutive_timeouts); }
