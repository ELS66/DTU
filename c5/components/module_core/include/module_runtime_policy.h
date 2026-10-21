#ifndef MODULE_RUNTIME_POLICY_H
#define MODULE_RUNTIME_POLICY_H
#include <stdbool.h>
#include <stdint.h>
#define MODULE_RECORD_INTERVAL_MS UINT64_C(10000)
#define MODULE_RECORD_DEBOUNCE_MS UINT64_C(250)
#define MODULE_RECORD_MIN_GAP_MS UINT64_C(2000)
#define MODULE_RECORD_RETRY_MS UINT64_C(5000)
typedef enum { MODULE_STATE_UNKNOWN, MODULE_STATE_FRESH, MODULE_STATE_STALE } module_state_freshness_t;
uint64_t module_state_timeout_ms(uint64_t configured, unsigned poll_ms, unsigned reply_ms);
uint64_t module_contact_timeout_ms(uint64_t state_timeout, unsigned poll_ms, unsigned reply_ms);
typedef struct {
    bool known;
    uint8_t state, source_command;
    uint16_t remaining_seconds;
    uint64_t observed_uptime_ms, revision;
} module_observation_t;
typedef enum { MODULE_SAVE_NONE, MODULE_SAVE_FIRST, MODULE_SAVE_CRITICAL, MODULE_SAVE_PERIODIC } module_save_reason_t;
typedef struct {
    module_observation_t live;
    bool event_known, critical_pending, has_saved, saving;
    uint8_t event_command, event_state;
    uint16_t event_remaining;
    uint64_t first_observed_ms, critical_revision, critical_since_ms;
    uint64_t saved_revision, captured_revision, last_success_ms, retry_after_ms;
    uint32_t duplicate_events, coalesced_changes;
} module_runtime_policy_t;
module_state_freshness_t module_observation_freshness(const module_observation_t *live, uint64_t now, uint64_t stale_ms);
bool module_runtime_observe(module_runtime_policy_t *policy, uint8_t command, uint8_t state,
                            uint16_t remaining, bool event, uint64_t now);
module_save_reason_t module_runtime_save_due(const module_runtime_policy_t *policy, uint64_t now, uint64_t stale_ms);
bool module_runtime_capture(module_runtime_policy_t *policy, uint64_t now, uint64_t stale_ms,
                            module_observation_t *out, module_save_reason_t *reason);
bool module_runtime_save_finished(module_runtime_policy_t *policy, uint64_t revision, bool success, uint64_t now);
typedef enum { MODULE_CONTACT_NOT_STARTED, MODULE_CONTACT_WAITING, MODULE_CONTACT_ONLINE, MODULE_CONTACT_OFFLINE } module_contact_state_t;
typedef struct {
    bool started, ever_valid, loss_latched;
    uint64_t started_ms, last_valid_ms;
    uint32_t consecutive_timeouts, loss_events, recoveries;
} module_peer_t;
void module_peer_start(module_peer_t *peer, uint64_t now);
module_contact_state_t module_peer_state(const module_peer_t *peer, uint64_t now, uint64_t timeout_ms);
void module_peer_tick(module_peer_t *peer, uint64_t now, uint64_t timeout_ms);
void module_peer_received(module_peer_t *peer, uint64_t now, uint64_t timeout_ms, bool reply);
void module_peer_timeout(module_peer_t *peer);
#endif
