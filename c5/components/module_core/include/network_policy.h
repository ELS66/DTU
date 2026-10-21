#ifndef NETWORK_POLICY_H
#define NETWORK_POLICY_H
#include <stdbool.h>
#include <stdint.h>
typedef enum { MODULE_SIM_UNKNOWN, MODULE_SIM_ABSENT, MODULE_SIM_PRESENT, MODULE_SIM_LOCKED } module_sim_t;
typedef enum { MODULE_NET_WAIT, MODULE_NET_WIFI, MODULE_NET_TRY_LTE, MODULE_NET_PROVISION } module_net_action_t;
module_net_action_t module_network_boot_action(module_sim_t sim, bool wifi_ready, bool detection_complete);
typedef struct { bool closed; } module_boot_gate_t;
/* One boot decision only. Any successful initial Wi-Fi connection closes the gate. */
module_net_action_t module_network_boot_step(module_boot_gate_t *gate, module_sim_t sim,
                                           bool wifi_ready, bool detection_complete);
typedef struct { unsigned absent_count; } module_sim_filter_t;
module_sim_t module_sim_confirm(module_sim_filter_t *filter, module_sim_t observation);
typedef enum { MODULE_LINK_NONE, MODULE_LINK_WIFI, MODULE_LINK_LTE } module_link_t;
typedef struct { module_link_t last_success; uint64_t wifi_retry_after_ms; } module_route_policy_t;
module_link_t module_route_choose(const module_route_policy_t *policy, uint64_t now_ms,
                                 bool wifi_ip, bool lte_pdp);
void module_route_result(module_route_policy_t *policy, module_link_t link, bool success, uint64_t now_ms);
#endif
